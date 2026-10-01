# Copyright (c) 2026, Vivaswan Works and contributors
# License: MIT. See license.txt

"""AI claim triage using Frappe Flow.

Provides:
- Flow-compatible tools that wrap the existing eligibility engine and claim context
- Orchestration that runs a Flow Agent and applies process / reject / pending actions
- Setup helpers that create the Flow Tool / Agent / Trigger records (idempotent)
"""

from __future__ import annotations

import json
import re
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime

# ---------------------------------------------------------------------------
# Thresholds (can later be moved to Insurance Settings)
# ---------------------------------------------------------------------------
HIGH_PROBABILITY = 80
LOW_PROBABILITY = 40
AGENT_TITLE = "Claim Triage Agent"
TRIGGER_TITLE = "Claim AI Triage on Submit/Update"


# ---------------------------------------------------------------------------
# Flow tools (imported via Flow Tool import_path)
# ---------------------------------------------------------------------------

def _eligibility_summary(claim_name: str) -> dict[str, Any]:
	"""Run deterministic eligibility and return a serialisable summary."""
	from insurance_core.eligibility import evaluate_claim_eligibility

	claim = frappe.get_doc("Insurance Claim", claim_name)
	result = evaluate_claim_eligibility(claim)

	criteria = []
	for row in result.criteria_results or []:
		criteria.append(
			{
				"criteria": row.get("eligibility_criteria") or row.get("criteria_code"),
				"result": row.get("result"),
				"is_mandatory": cint(row.get("is_mandatory")),
				"weightage": flt(row.get("weightage")),
				"score_contribution": flt(row.get("score_contribution")),
				"remarks": row.get("remarks") or "",
			}
		)

	return {
		"claim": claim_name,
		"overall_score": flt(result.overall_score),
		"overall_status": result.overall_status,
		"can_submit": bool(result.can_submit),
		"failed_mandatory": list(result.failed_mandatory or []),
		"warnings": list(result.warnings or []),
		"block_messages": list(result.block_messages or []),
		"criteria_results": criteria,
		"evaluation_name": result.evaluation_name,
	}


def get_claim_eligibility(claim_name: str) -> dict[str, Any]:
	"""Return the deterministic Claim Success Score and per-criteria results.

	Always call this first before making a triage recommendation.
	"""
	if not claim_name or not frappe.db.exists("Insurance Claim", claim_name):
		return {"error": f"Insurance Claim {claim_name!r} not found"}
	return _eligibility_summary(claim_name)


def get_claim_context(claim_name: str) -> dict[str, Any]:
	"""Return claim + linked policy / client / scheme / documents context for triage."""
	if not claim_name or not frappe.db.exists("Insurance Claim", claim_name):
		return {"error": f"Insurance Claim {claim_name!r} not found"}

	claim = frappe.get_doc("Insurance Claim", claim_name)
	policy = None
	client = None
	scheme = None

	if claim.policy and frappe.db.exists("Insurance Policy", claim.policy):
		policy = frappe.get_doc("Insurance Policy", claim.policy)
	if claim.client and frappe.db.exists("Insurance Client", claim.client):
		client = frappe.get_doc("Insurance Client", claim.client)
	scheme_name = claim.scheme or (policy.scheme if policy else None)
	if scheme_name and frappe.db.exists("Insurance Scheme", scheme_name):
		scheme = frappe.get_doc("Insurance Scheme", scheme_name)

	docs = []
	for d in claim.get("claim_documents") or []:
		docs.append(
			{
				"document_type": d.get("document_type"),
				"has_attachment": bool(d.get("attachment")),
				"verified": cint(d.get("verified")),
			}
		)

	members = []
	if policy:
		for m in policy.get("policy_members") or []:
			members.append({"member_name": m.get("member_name"), "relation": m.get("relation")})

	return {
		"claim": {
			"name": claim.name,
			"claim_number": claim.claim_number,
			"status": claim.status,
			"claim_type": claim.claim_type,
			"incident_date": str(claim.incident_date) if claim.incident_date else None,
			"reported_date": str(claim.reported_date) if claim.reported_date else None,
			"submission_date": str(claim.submission_date) if claim.submission_date else None,
			"claimed_amount": flt(claim.claimed_amount),
			"approved_amount": flt(claim.approved_amount),
			"description": (claim.description or "")[:2000],
			"diagnosis": claim.diagnosis,
			"treatment_details": (claim.treatment_details or "")[:1500],
			"hospital": claim.hospital,
			"claimant": claim.claimant,
			"eligibility_score": flt(claim.eligibility_score),
			"eligibility_status": claim.eligibility_status,
		},
		"policy": {
			"name": policy.name if policy else None,
			"status": policy.status if policy else None,
			"start_date": str(policy.start_date) if policy and policy.start_date else None,
			"end_date": str(policy.end_date) if policy and policy.end_date else None,
			"sum_assured": flt(policy.sum_assured) if policy else None,
			"payment_status": getattr(policy, "payment_status", None) if policy else None,
			"members": members,
		}
		if policy
		else None,
		"client": {
			"name": client.name if client else None,
			"lifecycle_stage": getattr(client, "lifecycle_stage", None) if client else None,
		}
		if client
		else None,
		"scheme": {
			"name": scheme.name if scheme else None,
			"line_of_business": getattr(scheme, "line_of_business", None) if scheme else None,
			"waiting_period_days": cint(getattr(scheme, "waiting_period_days", 0)) if scheme else 0,
		}
		if scheme
		else None,
		"documents": docs,
	}


def apply_triage_decision(
	claim_name: str,
	success_probability: float,
	recommended_action: str,
	reasons: str,
	missing_items: str = "",
	suggested_improvements: str = "",
	apply_status_change: int = 1,
) -> dict[str, Any]:
	"""Apply a triage decision to an Insurance Claim.

	recommended_action must be one of: process | reject | pending
	- process  → Under Review (high probability)
	- reject   → Rejected + rejection_reason
	- pending  → Additional Info Required + suggestion notes

	Writes assessment_notes, optional suggestion document, and AI fields.
	Does NOT settle or approve payouts — human still owns final authority.
	"""
	action = (recommended_action or "").strip().lower()
	if action not in ("process", "reject", "pending"):
		return {"error": f"Invalid recommended_action {recommended_action!r}. Use process|reject|pending."}

	if not claim_name or not frappe.db.exists("Insurance Claim", claim_name):
		return {"error": f"Insurance Claim {claim_name!r} not found"}

	claim = frappe.get_doc("Insurance Claim", claim_name)
	prob = flt(success_probability)
	now = now_datetime()

	_ensure_ai_fields()
	claim.db_set("ai_success_probability", prob, update_modified=False)
	claim.db_set("ai_recommended_action", action, update_modified=False)
	claim.db_set("ai_triage_at", now, update_modified=False)

	notes_parts = [
		f"[AI Triage {now}]",
		f"Success probability: {prob:.0f}%",
		f"Recommended action: {action}",
		f"Reasons: {reasons or '—'}",
	]
	if missing_items:
		notes_parts.append(f"Missing / incomplete: {missing_items}")
	if suggested_improvements:
		notes_parts.append(f"Suggestions: {suggested_improvements}")

	triage_block = "\n".join(notes_parts)
	existing_notes = (claim.assessment_notes or "").strip()
	new_notes = f"{existing_notes}\n\n{triage_block}".strip() if existing_notes else triage_block
	claim.db_set("assessment_notes", new_notes, update_modified=False)

	suggestion_name = None
	if action == "pending" and (missing_items or suggested_improvements):
		suggestion_name = _create_suggestion_document(
			claim, missing_items=missing_items, suggested_improvements=suggested_improvements, reasons=reasons
		)
		if suggestion_name:
			claim.db_set("ai_suggestion_document", suggestion_name, update_modified=False)

	status_changed = None
	if cint(apply_status_change):
		allowed_from = {
			"Draft",
			"Submitted",
			"Under Review",
			"Documents Pending",
			"Additional Info Required",
		}
		if claim.status in allowed_from:
			if action == "process":
				new_status = "Under Review"
			elif action == "reject":
				new_status = "Rejected"
				if reasons:
					claim.db_set("rejection_reason", (reasons or "")[:140], update_modified=False)
					claim.db_set("decision", "Reject", update_modified=False)
			else:
				new_status = "Additional Info Required"

			if new_status != claim.status:
				claim.db_set("status", new_status, update_modified=True)
				status_changed = new_status
				_log_assessment(claim.name, f"AI triage → {new_status}", triage_block)

	return {
		"claim": claim_name,
		"success_probability": prob,
		"recommended_action": action,
		"status_changed_to": status_changed,
		"suggestion_document": suggestion_name,
		"message": _("Triage applied: {0} ({1}%)").format(action, int(prob)),
	}


# ---------------------------------------------------------------------------
# Custom fields + logging helpers
# ---------------------------------------------------------------------------

def _ensure_ai_fields() -> None:
	"""Create the AI triage result fields on Insurance Claim (idempotent)."""
	if frappe.get_meta("Insurance Claim").has_field("ai_success_probability"):
		return

	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(
		{
			"Insurance Claim": [
				{
					"fieldname": "ai_success_probability",
					"label": "AI Success Probability",
					"fieldtype": "Percent",
					"insert_after": "eligibility_status",
					"read_only": 1,
					"no_copy": 1,
				},
				{
					"fieldname": "ai_recommended_action",
					"label": "AI Recommended Action",
					"fieldtype": "Select",
					"options": "\nprocess\nreject\npending",
					"insert_after": "ai_success_probability",
					"read_only": 1,
					"no_copy": 1,
				},
				{
					"fieldname": "ai_triage_at",
					"label": "AI Triage At",
					"fieldtype": "Datetime",
					"insert_after": "ai_recommended_action",
					"read_only": 1,
					"no_copy": 1,
				},
				{
					"fieldname": "ai_suggestion_document",
					"label": "AI Suggestion Document",
					"fieldtype": "Link",
					"options": "Claim Assessment Log",
					"insert_after": "ai_triage_at",
					"read_only": 1,
					"no_copy": 1,
				},
			]
		},
		update=True,
	)
	# create_custom_fields only registers the field metadata; without this the
	# physical column isn't added until the next full `bench migrate`.
	frappe.db.updatedb("Insurance Claim")
	frappe.clear_cache(doctype="Insurance Claim")


def _log_assessment(claim_name: str, to_status: str, comment: str) -> str | None:
	"""Append a Claim Assessment Log entry. Best-effort: never blocks triage."""
	try:
		doc = frappe.get_doc(
			{
				"doctype": "Claim Assessment Log",
				"claim": claim_name,
				"to_status": to_status,
				"comment": comment,
				"user": frappe.session.user,
				"logged_at": now_datetime(),
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name
	except Exception:
		frappe.log_error(title="AI triage assessment log failed")
		return None


def _create_suggestion_document(
	claim, missing_items: str = "", suggested_improvements: str = "", reasons: str = ""
) -> str | None:
	"""Record the AI's improvement suggestions as a Claim Assessment Log entry."""
	parts = []
	if missing_items:
		parts.append(f"Missing / incomplete: {missing_items}")
	if suggested_improvements:
		parts.append(f"Suggestions: {suggested_improvements}")
	if reasons:
		parts.append(f"Reasons: {reasons}")
	if not parts:
		return None
	return _log_assessment(claim.name, "Additional Info Required", "\n".join(parts))


# ---------------------------------------------------------------------------
# Flow wiring: tools, agent, trigger (idempotent setup)
# ---------------------------------------------------------------------------

TOOLS = [
	{
		"title": "Get Claim Eligibility",
		"slug": "get_claim_eligibility",
		"description": (
			"Return the deterministic Claim Success Score and per-criteria eligibility "
			"results for an Insurance Claim. Always call this first."
		),
		"import_path": "insurance_core.ai_triage.get_claim_eligibility",
	},
	{
		"title": "Get Claim Context",
		"slug": "get_claim_context",
		"description": (
			"Return the claim plus its linked policy, client, scheme and document context, "
			"for judging the plausibility and completeness of a claim."
		),
		"import_path": "insurance_core.ai_triage.get_claim_context",
	},
]

AGENT_INSTRUCTIONS = """You are an insurance claims triage assistant.

Given a claim name, you must:
1. Call get_claim_eligibility to get the deterministic Claim Success Score and any
   mandatory-criteria failures.
2. Call get_claim_context to review the claim narrative, linked policy, client and
   document completeness.
3. Decide a recommended_action: "process" (looks legitimate, no mandatory failures),
   "reject" (mandatory eligibility failures or clear ineligibility signals), or
   "pending" (plausible but missing information / documents).
4. Reply with ONLY a single JSON object (no prose, no markdown fences) with exactly
   these keys:
   {"recommended_action": "process|reject|pending",
    "success_probability": <0-100 number>,
    "reasons": "<short explanation citing the eligibility result>",
    "missing_items": "<comma separated missing documents/info, or empty string>",
    "suggested_improvements": "<what would raise the score, or empty string>"}

Never fabricate eligibility results -- they must come from the get_claim_eligibility tool.
If the deterministic result already blocks submission (can_submit is false), recommend
"reject" or "pending" accordingly, never "process".
"""


def ensure_flow_triage_setup() -> dict[str, Any]:
	"""Create/refresh the Flow Tool / Agent / Trigger records AI triage needs.

	Idempotent and safe to call from after_install / after_migrate. The Agent is
	only created once an enabled Flow Model exists; until then this just ensures
	the tools and custom fields are in place and reports what's still missing.
	"""
	_ensure_ai_fields()

	for tool in TOOLS:
		if frappe.db.exists("Flow Tool", tool["slug"]):
			doc = frappe.get_doc("Flow Tool", tool["slug"])
			doc.description = tool["description"]
			doc.import_path = tool["import_path"]
			doc.enabled = 1
			doc.save(ignore_permissions=True)
		else:
			frappe.get_doc(
				{
					"doctype": "Flow Tool",
					"title": tool["title"],
					"slug": tool["slug"],
					"type": "Imported",
					"description": tool["description"],
					"import_path": tool["import_path"],
					"enabled": 1,
				}
			).insert(ignore_permissions=True)

	model = frappe.db.get_value("Flow Model", {"enabled": 1}, "name", order_by="creation")
	if not model:
		frappe.db.commit()
		return {
			"status": "tools_ready",
			"tools": [t["slug"] for t in TOOLS],
			"message": _(
				"Flow Tools are ready. Create and enable a Flow Provider + Flow Model "
				"before the Claim Triage Agent can be created -- see docs/Flow_integration.md."
			),
		}

	agent_created = False
	if frappe.db.exists("Flow Agent", AGENT_TITLE):
		agent = frappe.get_doc("Flow Agent", AGENT_TITLE)
		agent.model = model
		agent.instructions = AGENT_INSTRUCTIONS
		agent.set("tools", [])
		for tool in TOOLS:
			agent.append("tools", {"tool": tool["slug"]})
		agent.enabled = 1
		agent.save(ignore_permissions=True)
	else:
		agent = frappe.get_doc(
			{
				"doctype": "Flow Agent",
				"title": AGENT_TITLE,
				"model": model,
				"instructions": AGENT_INSTRUCTIONS,
				"enabled": 1,
				"tools": [{"tool": tool["slug"]} for tool in TOOLS],
			}
		)
		agent.insert(ignore_permissions=True)
		agent_created = True

	trigger_created = False
	if not frappe.db.exists("Flow Trigger", TRIGGER_TITLE):
		frappe.get_doc(
			{
				"doctype": "Flow Trigger",
				"title": TRIGGER_TITLE,
				"agent": agent.name,
				"event": "DocType Event",
				"target_doctype": "Insurance Claim",
				"doc_event": "on_submit",
				# Off by default: auto-firing on every claim submit would call the
				# configured LLM for every claim. Enable explicitly once desired.
				"enabled": 0,
				"run_as": frappe.session.user if frappe.session.user != "Guest" else "Administrator",
				"prompt_template": "Run AI triage for Insurance Claim {{ doc.name }}.",
			}
		).insert(ignore_permissions=True)
		trigger_created = True

	frappe.db.commit()
	return {
		"status": "ready",
		"agent": agent.name,
		"model": model,
		"tools": [t["slug"] for t in TOOLS],
		"agent_created": agent_created,
		"trigger_created": trigger_created,
		"message": _(
			"Claim Triage Agent is ready. Use AI Triage / AI Triage (advisory only) on an Insurance Claim."
		),
	}


@frappe.whitelist()
def setup_claim_ai_triage() -> dict[str, Any]:
	"""Desk button entrypoint: (re)create the Flow Tool/Agent/Trigger records."""
	frappe.only_for(("System Manager", "Insurance Manager"))
	return ensure_flow_triage_setup()


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def _parse_decision(text: str | None) -> dict[str, Any]:
	if not text:
		raise ValueError("Agent returned no output")
	try:
		return json.loads(text)
	except json.JSONDecodeError:
		match = _JSON_BLOCK.search(text)
		if not match:
			raise ValueError(f"Could not find a JSON object in agent output: {text[:300]!r}")
		return json.loads(match.group(0))


@frappe.whitelist()
def run_claim_ai_triage(claim_name: str, apply_status_change: int = 1) -> dict[str, Any]:
	"""Run the Claim Triage Agent against a claim and apply (or just record) its decision.

	Backs both the "AI Triage" (apply_status_change=1) and "AI Triage (advisory only)"
	(apply_status_change=0) desk buttons on Insurance Claim.
	"""
	if not claim_name or not frappe.db.exists("Insurance Claim", claim_name):
		frappe.throw(_("Insurance Claim {0} not found").format(claim_name))

	eligibility = get_claim_eligibility(claim_name)

	if not frappe.db.exists("Flow Agent", AGENT_TITLE):
		frappe.throw(
			_("Claim Triage Agent is not set up yet. Use AI → Setup Flow Agent first."),
			title=_("AI Triage Not Configured"),
		)

	agent = frappe.get_doc("Flow Agent", AGENT_TITLE)
	prompt = (
		f"Triage Insurance Claim {claim_name}. Call get_claim_eligibility and "
		f"get_claim_context for this claim, then reply with the JSON decision only."
	)
	run = agent.run(prompt, source="Manual", reference_doctype="Insurance Claim", reference_name=claim_name)

	if run.status == "Failed":
		frappe.throw(_("AI triage failed: {0}").format(run.error or _("unknown error")), title=_("AI Triage Failed"))
	if run.status != "Completed":
		frappe.throw(
			_(
				"AI triage did not complete (status: {0}). The agent may be waiting on a "
				"confirmation this flow doesn't support."
			).format(run.status),
			title=_("AI Triage Incomplete"),
		)

	decision = _parse_decision(run.output)
	action = (decision.get("recommended_action") or "").strip().lower()
	probability = flt(decision.get("success_probability"))
	reasons = decision.get("reasons") or ""
	missing_items = decision.get("missing_items") or ""
	suggested_improvements = decision.get("suggested_improvements") or ""

	apply_result = apply_triage_decision(
		claim_name,
		success_probability=probability,
		recommended_action=action,
		reasons=reasons,
		missing_items=missing_items,
		suggested_improvements=suggested_improvements,
		apply_status_change=cint(apply_status_change),
	)
	if apply_result.get("error"):
		frappe.throw(apply_result["error"], title=_("AI Triage"))

	return {
		"decision": {
			"recommended_action": action,
			"success_probability": probability,
			"reasons": reasons,
			"missing_items": missing_items,
			"suggested_improvements": suggested_improvements,
		},
		"apply": apply_result,
		"eligibility": {
			"overall_score": eligibility.get("overall_score"),
			"overall_status": eligibility.get("overall_status"),
		},
		"run": run.name,
	}
