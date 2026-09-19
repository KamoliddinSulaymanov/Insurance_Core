"""Customer self-service portal API.

Resolves the logged-in user to an Insurance Client via email and exposes
read/write endpoints scoped to that client only.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime, nowdate


def _current_client():
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please log in to access the portal."), frappe.PermissionError)
	email = frappe.db.get_value("User", user, "email") or user
	client = frappe.db.get_value("Insurance Client", {"email": email}, "name")
	if not client:
		# System Manager can pass client for testing via form_dict
		if "System Manager" in frappe.get_roles() and frappe.form_dict.get("client"):
			return frappe.form_dict.get("client")
		frappe.throw(_("No insurance client profile is linked to your account."), frappe.PermissionError)
	return client


def _assert_owns_policy(policy_name, client):
	owner = frappe.db.get_value("Insurance Policy", policy_name, "client")
	if owner != client:
		frappe.throw(_("You do not have access to this policy."), frappe.PermissionError)


def _assert_owns_claim(claim_name, client):
	owner = frappe.db.get_value("Insurance Claim", claim_name, "client")
	if owner != client:
		frappe.throw(_("You do not have access to this claim."), frappe.PermissionError)


@frappe.whitelist(methods=["GET", "POST"])
def portal_me():
	"""Current user + linked insurance client for the app shell."""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please log in to access the portal."), frappe.PermissionError)

	user_doc = frappe.db.get_value(
		"User",
		user,
		["name", "full_name", "email", "user_image", "first_name", "last_name"],
		as_dict=True,
	) or {}

	email = user_doc.get("email") or user
	client_name = frappe.db.get_value("Insurance Client", {"email": email}, "name")
	client = None
	if client_name:
		client = frappe.get_cached_value(
			"Insurance Client",
			client_name,
			["name", "full_name", "email", "phone", "lifecycle_stage"],
			as_dict=True,
		)
	elif "System Manager" in frappe.get_roles() and frappe.form_dict.get("client"):
		client = frappe.get_cached_value(
			"Insurance Client",
			frappe.form_dict.get("client"),
			["name", "full_name", "email", "phone", "lifecycle_stage"],
			as_dict=True,
		)

	return {
		"user": {
			"name": user_doc.get("name") or user,
			"full_name": user_doc.get("full_name") or user,
			"email": email,
			"user_image": user_doc.get("user_image"),
		},
		"client": client,
	}


@frappe.whitelist(methods=["GET", "POST"])
def portal_search(q=None, limit=10):
	"""Search the current client's policies and claims."""
	client = _current_client()
	q = (q or "").strip()
	if not q or len(q) < 2:
		return {"policies": [], "claims": []}

	limit = min(cint(limit) or 10, 25)
	like = f"%{q}%"

	policies = frappe.get_all(
		"Insurance Policy",
		filters={"client": client},
		or_filters=[
			["policy_number", "like", like],
			["name", "like", like],
			["scheme", "like", like],
			["provider", "like", like],
		],
		fields=["name", "policy_number", "status", "scheme", "end_date"],
		order_by="modified desc",
		limit_page_length=limit,
	)
	claims = frappe.get_all(
		"Insurance Claim",
		filters={"client": client},
		or_filters=[
			["claim_number", "like", like],
			["name", "like", like],
			["claim_type", "like", like],
			["policy", "like", like],
		],
		fields=["name", "claim_number", "status", "claim_type", "incident_date", "claimed_amount"],
		order_by="modified desc",
		limit_page_length=limit,
	)
	return {"policies": policies, "claims": claims}


@frappe.whitelist(methods=["GET", "POST"])
def portal_dashboard():
	client = _current_client()
	policies = frappe.get_all(
		"Insurance Policy",
		filters={"client": client},
		fields=["name", "policy_number", "status", "sum_assured", "total_premium", "end_date", "scheme"],
		order_by="modified desc",
	)
	claims = frappe.get_all(
		"Insurance Claim",
		filters={"client": client},
		fields=["name", "claim_number", "status", "claimed_amount", "incident_date", "policy"],
		order_by="modified desc",
		limit=10,
	)
	active = [p for p in policies if p.status in ("Active", "Grace Period")]
	return {
		"client": frappe.get_cached_value(
			"Insurance Client", client, ["name", "full_name", "email", "phone", "lifecycle_stage"], as_dict=True
		),
		"stats": {
			"active_policies": len(active),
			"total_policies": len(policies),
			"open_claims": len([c for c in claims if c.status not in ("Settled", "Closed", "Rejected")]),
		},
		"policies": policies[:5],
		"claims": claims,
	}


@frappe.whitelist(methods=["GET", "POST"])
def portal_list_policies():
	client = _current_client()
	return frappe.get_all(
		"Insurance Policy",
		filters={"client": client},
		fields=[
			"name",
			"policy_number",
			"status",
			"scheme",
			"provider",
			"sum_assured",
			"premium_amount",
			"total_premium",
			"start_date",
			"end_date",
			"payment_status",
			"policy_document",
		],
		order_by="end_date desc",
	)


@frappe.whitelist(methods=["GET", "POST"])
def portal_get_policy(policy):
	client = _current_client()
	_assert_owns_policy(policy, client)
	doc = frappe.get_doc("Insurance Policy", policy)
	return {
		"policy": doc.as_dict(),
		"members": [m.as_dict() for m in doc.get("policy_members") or []],
		"coverages": [c.as_dict() for c in doc.get("policy_coverages") or []],
		"documents": [d.as_dict() for d in doc.get("other_documents") or []],
	}


@frappe.whitelist(methods=["GET", "POST"])
def portal_list_claims():
	client = _current_client()
	return frappe.get_all(
		"Insurance Claim",
		filters={"client": client},
		fields=[
			"name",
			"claim_number",
			"policy",
			"claim_type",
			"status",
			"claimed_amount",
			"approved_amount",
			"incident_date",
			"submission_date",
		],
		order_by="modified desc",
	)


@frappe.whitelist(methods=["GET", "POST"])
def portal_get_claim(claim):
	client = _current_client()
	_assert_owns_claim(claim, client)
	doc = frappe.get_doc("Insurance Claim", claim)
	policy_number = frappe.db.get_value("Insurance Policy", doc.policy, "policy_number") if doc.policy else None
	return {
		"claim": doc.as_dict(),
		"policy_number": policy_number,
		"documents": [d.as_dict() for d in doc.get("claim_documents") or []],
	}


@frappe.whitelist()
def portal_upload_claim_document(claim, document_type, file_url=None):
	"""Append a Claim Document row. Pass file_url from /api/method/upload_file."""
	client = _current_client()
	_assert_owns_claim(claim, client)

	status = frappe.db.get_value("Insurance Claim", claim, "status")
	if status in ("Settled", "Closed", "Rejected"):
		frappe.throw(_("Documents cannot be uploaded on a {0} claim.").format(status))

	document_type = (document_type or "").strip()
	allowed = {
		"Discharge Summary",
		"Bills",
		"Reports",
		"ID Proof",
		"FIR",
		"Estimate",
		"Other",
	}
	if document_type not in allowed:
		frappe.throw(_("Invalid document type."))

	if not file_url:
		frappe.throw(_("Please upload a file."))

	doc = frappe.get_doc("Insurance Claim", claim)
	doc.append(
		"claim_documents",
		{
			"document_type": document_type,
			"attachment": file_url,
			"uploaded_by": frappe.session.user,
			"uploaded_on": now_datetime(),
		},
	)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {
		"name": doc.name,
		"documents": [d.as_dict() for d in doc.get("claim_documents") or []],
	}


@frappe.whitelist()
def portal_intimate_claim(policy, claim_type, incident_date, claimed_amount, description=None, claimant=None):
	client = _current_client()
	_assert_owns_policy(policy, client)
	policy_doc = frappe.get_doc("Insurance Policy", policy)
	if policy_doc.status not in ("Active", "Grace Period", "Claimed"):
		frappe.throw(_("Claims can only be intimated on active policies."), title=_("Invalid Policy"))

	doc = frappe.get_doc(
		{
			"doctype": "Insurance Claim",
			"claim_number": f"P-{frappe.generate_hash(length=8)}",
			"policy": policy,
			"client": client,
			"provider": policy_doc.provider,
			"scheme": policy_doc.scheme,
			"claim_type": claim_type or "Reimbursement",
			"incident_date": incident_date or nowdate(),
			"submission_date": nowdate(),
			"reported_date": nowdate(),
			"claimed_amount": flt(claimed_amount),
			"status": "Submitted",
			"intimation_mode": "Portal",
			"description": description,
			"claimant": claimant,
			"agent": policy_doc.agent,
		}
	)
	doc.insert(ignore_permissions=True)
	return {"name": doc.name, "claim_number": doc.claim_number}


@frappe.whitelist()
def portal_request_endorsement(policy, endorsement_type, description, new_value=None, effective_date=None):
	client = _current_client()
	_assert_owns_policy(policy, client)
	doc = frappe.get_doc(
		{
			"doctype": "Policy Endorsement",
			"policy": policy,
			"endorsement_type": endorsement_type,
			"description": description or endorsement_type,
			"new_value": new_value,
			"effective_date": effective_date or nowdate(),
			"status": "Submitted",
		}
	)
	doc.insert(ignore_permissions=True)
	return {"name": doc.name, "endorsement_number": doc.endorsement_number, "premium_impact": doc.premium_impact}


@frappe.whitelist(methods=["GET", "POST"])
def portal_policy_print(policy):
	client = _current_client()
	_assert_owns_policy(policy, client)
	from insurance_core.print_formats import get_print_html

	return get_print_html("Insurance Policy", policy)


@frappe.whitelist(methods=["GET", "POST"])
def portal_claim_print(claim, settlement=0):
	client = _current_client()
	_assert_owns_claim(claim, client)
	from insurance_core.print_formats import get_print_html

	key = "claim_settlement" if cint(settlement) else "Insurance Claim"
	return get_print_html("Insurance Claim", claim, template_key=key)
