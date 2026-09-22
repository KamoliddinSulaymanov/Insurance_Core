from urllib.parse import urlparse

import frappe
from frappe import _, safe_eval
from frappe.utils import (
	add_days,
	cint,
	date_diff,
	flt,
	getdate,
	now_datetime,
	nowdate,
)

CACHE_KEY = "insurance_eligibility_criteria"
SCHEME_TYPE_MAP = {
	"Life": "Life",
	"Health": "Health",
	"Auto": "Motor",
	"Motor": "Motor",
	"Property": "Property",
	"Liability": "Liability",
	"Travel": "Travel",
	"Cyber": "Cyber",
	"Marine": "Marine",
}


class EligibilityResult:
	def __init__(self):
		self.overall_score = 0.0
		self.overall_status = "Eligible"
		self.can_submit = True
		self.criteria_results = []
		self.failed_mandatory = []
		self.warnings = []
		self.evaluation_name = None
		self.block_messages = []


def _engine_enabled():
	if not frappe.db.exists("DocType", "Insurance Settings"):
		return True
	if not frappe.get_meta("Insurance Settings").has_field("enable_eligibility_engine"):
		return True
	return cint(frappe.db.get_single_value("Insurance Settings", "enable_eligibility_engine") or 1)


def _settings():
	defaults = {
		"eligibility_score_threshold": 70,
		"enable_eligibility_engine": 1,
		"eligibility_override_role": "Insurance Manager",
		"max_intimation_days": 30,
		"normalize_weightage": 1,
	}
	if not frappe.db.exists("DocType", "Insurance Settings"):
		return defaults
	out = dict(defaults)
	meta = frappe.get_meta("Insurance Settings")
	for key in defaults:
		if meta.has_field(key):
			val = frappe.db.get_single_value("Insurance Settings", key)
			if val not in (None, ""):
				out[key] = val
	return out


def _stage_matches(criteria_stage, requested_stage):
	if not requested_stage:
		return True
	if criteria_stage == "Both":
		return requested_stage in ("Claim Intake", "Policy Issuance", "Both", "Pre-Authorization")
	return criteria_stage == requested_stage or requested_stage == "Both"


def _scheme_type_for(scheme):
	if not scheme:
		return None
	lob = frappe.db.get_value("Insurance Scheme", scheme, "line_of_business")
	return SCHEME_TYPE_MAP.get(lob, lob)


def clear_criteria_cache():
	frappe.cache().delete_value(CACHE_KEY)


def _all_active_criteria():
	cached = frappe.cache().get_value(CACHE_KEY)
	if cached:
		return [frappe._dict(row) for row in cached]
	if not frappe.db.exists("DocType", "Client Eligibility Criteria"):
		return []
	fields = [
		"name",
		"criteria_name",
		"criteria_code",
		"applies_to",
		"scheme_type",
		"insurance_scheme",
		"insurance_provider",
		"claim_type",
		"evaluation_stage",
		"is_mandatory",
		"weightage",
		"pass_score",
		"failure_action",
		"override_role",
		"severity",
		"evaluation_method",
		"source_doctype",
		"field_to_check",
		"expected_value",
		"operator",
		"python_expression",
		"custom_script",
		"external_api",
		"description",
	]
	if frappe.db.has_column("Client Eligibility Criteria", "criteria_version"):
		fields.append("criteria_version")
	rows = frappe.get_all(
		"Client Eligibility Criteria",
		filters={"status": "Active"},
		fields=fields,
	)
	frappe.cache().set_value(CACHE_KEY, rows, expires_in_sec=3600)
	return rows


def get_applicable_criteria(scheme=None, claim_type=None, provider=None, evaluation_stage="Claim Intake"):
	rows = _all_active_criteria()
	scheme_type = _scheme_type_for(scheme)
	matched = []
	for row in rows:
		if not _stage_matches(row.evaluation_stage, evaluation_stage):
			continue
		if row.applies_to == "Specific Scheme" and row.insurance_scheme != scheme:
			continue
		if row.applies_to == "Specific Provider" and row.insurance_provider != provider:
			continue
		if row.applies_to == "Specific Scheme Type" and row.scheme_type != scheme_type:
			continue
		if row.claim_type and row.claim_type != "All":
			if not claim_type or row.claim_type != claim_type:
				continue
		matched.append(row)
	return matched


def _load_related(claim_doc):
	policy = None
	client = None
	scheme = None
	if claim_doc.get("policy") and frappe.db.exists("Insurance Policy", claim_doc.policy):
		policy = frappe.get_doc("Insurance Policy", claim_doc.policy)
	if claim_doc.get("client") and frappe.db.exists("Insurance Client", claim_doc.client):
		client = frappe.get_doc("Insurance Client", claim_doc.client)
	scheme_name = claim_doc.get("scheme") or (policy.scheme if policy else None)
	if scheme_name and frappe.db.exists("Insurance Scheme", scheme_name):
		scheme = frappe.get_doc("Insurance Scheme", scheme_name)
	return policy, client, scheme


def _source_doc(criteria, claim_doc, policy, client, scheme):
	mapping = {
		"Insurance Claim": claim_doc,
		"Insurance Policy": policy,
		"Insurance Client": client,
		"Insurance Scheme": scheme,
		"Customer": client,
		"Patient": client,
		"Employee": client,
	}
	if criteria.get("source_doctype") == "Client KYC" and client:
		kyc_name = frappe.db.get_value("Client KYC", {"client": client.name}, "name")
		if kyc_name:
			mapping["Client KYC"] = frappe.get_doc("Client KYC", kyc_name)
	source = criteria.get("source_doctype")
	if source in mapping:
		return mapping[source]
	if source and frappe.db.exists("DocType", source) and claim_doc.get("name"):
		filters = {}
		meta = frappe.get_meta(source)
		for field in ("client", "insurance_client", "policy", "insurance_policy", "claim", "insurance_claim"):
			if meta.has_field(field):
				value = claim_doc.get(field.replace("insurance_", "")) or claim_doc.get(field)
				if field in ("client", "insurance_client"):
					value = claim_doc.get("client")
				elif field in ("policy", "insurance_policy"):
					value = claim_doc.get("policy")
				elif field in ("claim", "insurance_claim"):
					value = claim_doc.get("name")
				if value:
					filters[field] = value
					break
		if filters:
			name = frappe.db.get_value(source, filters, "name")
			if name:
				return frappe.get_doc(source, name)
	return claim_doc


def _compare(actual, operator, expected):
	op = (operator or "Equals").strip()
	if op == "Is Set":
		return actual not in (None, "", [], {})
	if op == "Is Not Set":
		return actual in (None, "", [], {})
	if actual is None:
		actual = ""
	if expected is None:
		expected = ""
	if op == "Equals":
		return str(actual).strip().lower() == str(expected).strip().lower()
	if op == "Not Equals":
		return str(actual).strip().lower() != str(expected).strip().lower()
	if op in ("Greater Than", "Less Than"):
		try:
			left, right = flt(actual), flt(expected)
		except Exception:
			left, right = str(actual), str(expected)
		return left > right if op == "Greater Than" else left < right
	if op in ("In", "Not In"):
		values = [v.strip().lower() for v in str(expected).split(",") if v.strip()]
		present = str(actual).strip().lower() in values
		return present if op == "In" else not present
	if op == "Contains":
		return str(expected).strip().lower() in str(actual).strip().lower()
	return False


def _eval_field_check(criteria, claim_doc, policy, client, scheme):
	doc = _source_doc(criteria, claim_doc, policy, client, scheme)
	if not doc:
		return False, _("Source document {0} was not found.").format(criteria.get("source_doctype") or "")
	field = criteria.get("field_to_check")
	if not field:
		return False, _("Field to Check is not configured.")
	actual = doc.get(field) if hasattr(doc, "get") else getattr(doc, field, None)
	passed = _compare(actual, criteria.get("operator"), criteria.get("expected_value"))
	if passed:
		return True, _("Field {0} matches expected value.").format(field)
	return False, _("{0} is {1}; expected {2} {3}.").format(
		field, actual if actual not in (None, "") else _("not set"), criteria.get("operator") or "Equals", criteria.get("expected_value") or ""
	)


def _eval_expression(criteria, claim_doc, policy, client, scheme):
	expr = (criteria.get("python_expression") or "").strip()
	if not expr:
		return False, _("Python expression is empty.")
	settings = _settings()
	context = {
		"doc": claim_doc,
		"claim": claim_doc,
		"policy": policy,
		"client": client,
		"scheme": scheme,
		"flt": flt,
		"cint": cint,
		"getdate": getdate,
		"nowdate": nowdate,
		"date_diff": date_diff,
		"add_days": add_days,
		"any": any,
		"all": all,
		"bool": bool,
		"int": int,
		"str": str,
		"len": len,
		"max_intimation_days": cint(settings.get("max_intimation_days") or 30),
	}
	try:
		result = safe_eval(expr, None, context)
	except Exception as e:
		return "error", _("Expression failed: {0}").format(str(e))
	passed = bool(result)
	return passed, _("Expression evaluated to {0}.").format(passed)


def _eval_script(criteria, claim_doc, policy, client, scheme):
	path = (criteria.get("custom_script") or "").strip()
	if not path or "." not in path:
		return "error", _("Custom script path is invalid.")
	try:
		fn = frappe.get_attr(path)
		result = fn(claim_doc, policy=policy, client=client, scheme=scheme, criteria=criteria)
	except Exception as e:
		return "error", _("Custom script failed: {0}").format(str(e))
	if isinstance(result, tuple):
		passed, remarks = result[0], result[1] if len(result) > 1 else ""
		return bool(passed), remarks or _("Custom script returned {0}.").format(bool(passed))
	if isinstance(result, dict):
		return bool(result.get("passed")), result.get("remarks") or ""
	return bool(result), _("Custom script returned {0}.").format(bool(result))


def _is_safe_url(url):
	parsed = urlparse(url or "")
	if parsed.scheme not in ("http", "https"):
		return False
	host = (parsed.hostname or "").lower()
	if not host:
		return False
	blocked = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
	if host in blocked or host.endswith(".local") or host.startswith("10.") or host.startswith("192.168.") or host.startswith("172."):
		return False
	return True


def _eval_external_api(criteria, claim_doc, policy, client, scheme):
	url = (criteria.get("external_api") or "").strip()
	if not _is_safe_url(url):
		return "error", _("External API endpoint is not allowed.")
	try:
		import requests

		payload = {
			"claim": claim_doc.name if claim_doc else None,
			"policy": policy.name if policy else None,
			"client": client.name if client else None,
			"criteria": criteria.get("criteria_code"),
		}
		resp = requests.post(url, json=payload, timeout=8)
		data = resp.json() if resp.content else {}
		passed = bool(data.get("passed", resp.ok and resp.status_code == 200))
		remarks = data.get("remarks") or _("External API returned HTTP {0}.").format(resp.status_code)
		return passed, remarks
	except Exception as e:
		return "error", _("External API call failed: {0}").format(str(e))


def _eval_checklist(criteria, claim_doc):
	items = frappe.get_all(
		"Eligibility Checklist Item",
		filters={"parent": criteria.get("name"), "parenttype": "Client Eligibility Criteria"},
		fields=["item", "is_mandatory", "weightage", "evidence_required"],
		order_by="idx",
	)
	if not items:
		return False, _("No checklist items configured.")
	docs = [d.document_type for d in (claim_doc.get("claim_documents") or []) if d.get("document_type") or d.get("attachment")]
	attachments = [d.attachment for d in (claim_doc.get("claim_documents") or []) if d.get("attachment")]
	completed = [c.item for c in (claim_doc.get("compliance_checklist") or []) if c.get("completed")]
	failed = []
	total = 0.0
	earned = 0.0
	for item in items:
		w = flt(item.weightage) or (100.0 / len(items))
		total += w
		label = (item.item or "").strip()
		matched = label in docs or label in completed or any(label.lower() in (d or "").lower() for d in docs)
		if item.evidence_required and not attachments and not matched:
			matched = False
		if matched:
			earned += w
		elif item.is_mandatory:
			failed.append(label)
	score = (earned / total * 100.0) if total else 0.0
	pass_score = flt(criteria.get("pass_score") or 100)
	if failed:
		return False, _("Mandatory checklist items missing: {0}").format(", ".join(failed))
	if score < pass_score:
		return False, _("Checklist score {0}% is below required {1}%.").format(flt(score, 2), pass_score)
	return True, _("Checklist complete ({0}%).").format(flt(score, 2))


def _builtin_check(criteria, claim_doc, policy, client, scheme):
	code = (criteria.get("criteria_code") or "").upper()
	if code == "POLICY_ACTIVE":
		if not policy:
			return False, _("No policy is linked to this claim.")
		if policy.status in ("Active", "Grace Period", "Claimed"):
			return True, _("Policy status is {0}.").format(policy.status)
		return False, _("Policy is not Active – current status is {0}.").format(policy.status)
	if code == "WITHIN_COVERAGE":
		if not policy or not claim_doc.get("incident_date"):
			return False, _("Policy period or incident date is missing.")
		incident = getdate(claim_doc.incident_date)
		if getdate(policy.start_date) <= incident <= getdate(policy.end_date):
			return True, _("Incident date is within the policy period.")
		return False, _("Incident date {0} is outside policy period {1} to {2}.").format(
			claim_doc.incident_date, policy.start_date, policy.end_date
		)
	if code == "WAITING_PERIOD":
		waiting = cint(scheme.waiting_period_days) if scheme else 0
		if not waiting:
			return True, _("No waiting period configured.")
		if not policy or not claim_doc.get("incident_date"):
			return False, _("Cannot verify waiting period without policy start and incident date.")
		elapsed = date_diff(getdate(claim_doc.incident_date), getdate(policy.start_date))
		if elapsed >= waiting:
			return True, _("Waiting period of {0} days is complete.").format(waiting)
		return False, _("Waiting period of {0} days is not complete – only {1} days have elapsed.").format(waiting, elapsed)
	if code == "PRE_EXISTING":
		waiting = cint(scheme.pre_existing_waiting) if scheme else 0
		if not waiting:
			return True, _("No pre-existing disease waiting period configured.")
		if not policy or not claim_doc.get("incident_date"):
			return False, _("Cannot verify pre-existing waiting without dates.")
		elapsed = date_diff(getdate(claim_doc.incident_date), getdate(policy.start_date))
		if elapsed >= waiting:
			return True, _("Pre-existing disease waiting is complete.")
		return False, _("Pre-existing disease waiting of {0} days is not complete.").format(waiting)
	if code == "SUM_INSURED_AVAILABLE":
		if not policy or not flt(policy.sum_assured):
			return True, _("No sum assured limit on policy.")
		claimed = flt(claim_doc.get("claimed_amount"))
		paid = 0
		if claim_doc.get("policy"):
			paid = flt(frappe.db.sql(
				"""
				select coalesce(sum(settled_amount), 0) from `tabInsurance Claim`
				where policy = %s and name != %s and status in ('Settled', 'Approved', 'Partially Approved')
				""",
				(claim_doc.policy, claim_doc.get("name") or ""),
			)[0][0])
		remaining = flt(policy.sum_assured) - paid
		if claimed <= remaining:
			return True, _("Claimed amount is within remaining coverage {0}.").format(remaining)
		return False, _("Claimed amount {0} exceeds remaining coverage {1}.").format(claimed, remaining)
	if code == "NO_FRAUD_FLAG":
		if not client:
			return False, _("Client is not linked.")
		if client.lifecycle_stage == "Blacklisted":
			return False, _("Client is blacklisted – claim cannot be filed.")
		return True, _("Client is not blacklisted.")
	if code == "MEMBER_COVERED":
		if not policy or not policy.get("policy_members"):
			return True, _("No member list on policy.")
		claimant = (claim_doc.get("claimant") or "").strip().lower()
		if not claimant:
			return True, _("No claimant specified.")
		names = [(m.member_name or "").strip().lower() for m in policy.get("policy_members")]
		if claimant in names:
			return True, _("Claimant is a covered member.")
		return False, _("Claimant {0} is not listed as a covered member.").format(claim_doc.get("claimant"))
	if code == "NETWORK_HOSPITAL":
		if claim_doc.get("claim_type") != "Cashless":
			return True, _("Not a cashless claim.")
		if claim_doc.get("hospital"):
			status = frappe.db.get_value("Network Hospital", claim_doc.hospital, "status") if claim_doc.hospital else None
			if status and status != "Active":
				return False, _("Selected hospital is not an active network hospital.")
			return True, _("Treatment is at a network hospital.")
		return False, _("Cashless claims should be treated at a network hospital.")
	if code == "INTIMATION_TIMELY":
		if not claim_doc.get("incident_date"):
			return True, _("Incident date not set.")
		reported = claim_doc.get("reported_date") or claim_doc.get("submission_date")
		if not reported:
			return True, _("Reported date not set.")
		max_days = cint(_settings().get("max_intimation_days") or 30)
		elapsed = date_diff(getdate(reported), getdate(claim_doc.incident_date))
		if elapsed <= max_days:
			return True, _("Claim intimated within {0} days.").format(max_days)
		return False, _("Claim intimated {0} days after incident – maximum allowed is {1} days.").format(elapsed, max_days)
	if code == "AGE_ELIGIBLE":
		if not scheme or not client or not client.get("date_of_birth"):
			return True, _("Age limits not applicable.")
		age = int(date_diff(nowdate(), client.date_of_birth) / 365.25)
		mn, mx = cint(scheme.get("minimum_age")), cint(scheme.get("maximum_age"))
		if mn and age < mn:
			return False, _("Member age {0} is below scheme minimum {1}.").format(age, mn)
		if mx and age > mx:
			return False, _("Member age {0} exceeds scheme maximum {1}.").format(age, mx)
		return True, _("Member age {0} is within scheme limits.").format(age)
	if code == "EXCLUSION_CHECK":
		if not scheme or not claim_doc.get("description") or not scheme.get("exclusion_items"):
			return True, _("No exclusion keywords matched.")
		text = (claim_doc.description or "").lower()
		hits = [e.exclusion for e in scheme.get("exclusion_items") if (e.exclusion or "").strip().lower() in text]
		if hits:
			return False, _("Incident appears under exclusions: {0}.").format(", ".join(hits))
		return True, _("Incident is not under listed exclusions.")
	if code == "CONSENT_VALID":
		if not client:
			return True, _("No client to check consent.")
		if client.get("consent_data_processing") or client.get("consent_share_tpa"):
			return True, _("Valid consent is present.")
		return False, _("Valid consent / authorization is not present.")
	if code == "KYC_COMPLETE":
		status = client.get("kyc_status") if client else None
		if status == "Verified":
			return True, _("KYC is verified.")
		return False, _("KYC is not verified – please complete KYC before filing claim.")
	if code == "PREMIUM_PAID":
		status = policy.get("payment_status") if policy else None
		if status == "Paid":
			return True, _("Premium is paid.")
		return False, _("Premium is not paid – current payment status is {0}.").format(status or _("not set"))
	return None


def _evaluate_one(criteria, claim_doc, policy, client, scheme):
	method = criteria.get("evaluation_method") or "Field Check"
	try:
		builtin = _builtin_check(criteria, claim_doc, policy, client, scheme)
		if builtin is not None:
			return builtin
		if method == "Field Check":
			return _eval_field_check(criteria, claim_doc, policy, client, scheme)
		if method == "Expression":
			return _eval_expression(criteria, claim_doc, policy, client, scheme)
		if method == "Script":
			return _eval_script(criteria, claim_doc, policy, client, scheme)
		if method == "External API":
			return _eval_external_api(criteria, claim_doc, policy, client, scheme)
		if method == "Checklist":
			return _eval_checklist(criteria, claim_doc)
	except Exception as e:
		return "error", _("Evaluation error: {0}").format(str(e))
	return False, _("Unknown evaluation method {0}.").format(method)


def _normalize_weights(rows, normalize):
	total = sum(flt(r.weightage) for r in rows) or 0
	if not normalize or total <= 0:
		return {r.name: flt(r.weightage) for r in rows}
	return {r.name: flt(r.weightage) / total * 100.0 for r in rows}


def _user_can_override(criteria_list):
	roles = set(frappe.get_roles())
	if "System Manager" in roles or "Insurance Manager" in roles:
		return True
	for c in criteria_list:
		if c.get("override_role") and c.override_role in roles:
			return True
	settings = _settings()
	if settings.get("eligibility_override_role") in roles:
		return True
	return False


def evaluate_claim_eligibility(claim_doc, throw=True, evaluation_stage="Claim Intake"):
	result = EligibilityResult()
	if isinstance(claim_doc, str):
		claim_doc = frappe.get_doc("Insurance Claim", claim_doc)
	if not _engine_enabled():
		result.overall_status = "Eligible"
		result.can_submit = True
		result.overall_score = 100
		return result

	policy, client, scheme = _load_related(claim_doc)
	scheme_name = claim_doc.get("scheme") or (policy.scheme if policy else None)
	provider = claim_doc.get("provider") or (policy.provider if policy else None)
	criteria_list = get_applicable_criteria(
		scheme=scheme_name,
		claim_type=claim_doc.get("claim_type"),
		provider=provider,
		evaluation_stage=evaluation_stage,
	)
	settings = _settings()
	weights = _normalize_weights(criteria_list, cint(settings.get("normalize_weightage")))
	score = 0.0
	has_warning = False
	override_needed = []

	for criteria in criteria_list:
		passed, remarks = _evaluate_one(criteria, claim_doc, policy, client, scheme)
		status = "Pass"
		contribution = 0.0
		weight = flt(weights.get(criteria.name))
		if passed == "error":
			status = "Error"
			remarks = remarks
			if criteria.is_mandatory:
				result.failed_mandatory.append(criteria)
		elif passed:
			status = "Pass"
			contribution = weight
			score += contribution
		else:
			status = "Fail"
			if criteria.is_mandatory:
				result.failed_mandatory.append(criteria)
			if criteria.failure_action == "Warning Only":
				has_warning = True
				result.warnings.append(remarks or criteria.criteria_name)
			if criteria.failure_action == "Require Override":
				override_needed.append(criteria)
				has_warning = True
			if criteria.failure_action == "Block Submission":
				result.block_messages.append(
					_("{0} – {1}").format(criteria.criteria_name, remarks or _("not met"))
				)
			if criteria.failure_action == "Auto-Reject":
				result.block_messages.append(
					_("{0} – {1}").format(criteria.criteria_name, remarks or _("auto-rejected"))
				)
				_apply_auto_reject(claim_doc, remarks)

		result.criteria_results.append({
			"eligibility_criteria": criteria.name,
			"criteria_code": criteria.get("criteria_code"),
			"criteria_version": cint(criteria.get("criteria_version") or 1),
			"is_mandatory": 1 if criteria.is_mandatory else 0,
			"weightage": weight,
			"result": status,
			"score_contribution": contribution,
			"remarks": remarks,
		})

	threshold = flt(settings.get("eligibility_score_threshold") or 70)
	result.overall_score = flt(score, 2)
	if not criteria_list:
		result.overall_score = 100
		result.overall_status = "Eligible"
		result.can_submit = True
	else:
		blocked = bool(result.block_messages) or any(
			c.failure_action in ("Block Submission", "Auto-Reject") for c in result.failed_mandatory
		)
		if blocked:
			result.overall_status = "Not Eligible"
			result.can_submit = False
		elif result.failed_mandatory or has_warning or result.overall_score < threshold:
			result.overall_status = "Conditionally Eligible"
			needs_override = bool(override_needed) or bool(result.failed_mandatory)
			result.can_submit = not needs_override
		else:
			result.overall_status = "Eligible"
			result.can_submit = True

	ignore = bool(getattr(claim_doc.flags, "ignore_eligibility", False))
	overridden = bool(claim_doc.get("eligibility_overridden"))
	if overridden and claim_doc.get("eligibility_override_reason") and _user_can_override(criteria_list):
		result.can_submit = True
		if result.overall_status == "Not Eligible":
			result.overall_status = "Conditionally Eligible"
		_log_override_comment(claim_doc)

	is_new = True
	if hasattr(claim_doc, "is_new"):
		is_new = claim_doc.is_new()
	if claim_doc.get("name") and not is_new:
		result.evaluation_name = _write_evaluation_log(claim_doc, policy, result)

	if throw and not result.can_submit and not ignore:
		messages = result.block_messages or [
			_("{0} – {1}").format(c.criteria_name, _("mandatory criteria failed"))
			for c in result.failed_mandatory
		]
		if not messages and result.overall_status != "Eligible":
			messages = [_("Claim Success Score {0}% is below the required {1}%.").format(result.overall_score, threshold)]
		frappe.throw(
			_("This claim is not eligible for submission:<br>{0}").format("<br>".join(messages)),
			title=_("Eligibility Check Failed"),
		)
	return result


def _apply_auto_reject(claim_doc, remarks):
	meta = getattr(claim_doc, "meta", None)
	if not meta or not hasattr(meta, "has_field"):
		return
	if not meta.has_field("status"):
		return
	if claim_doc.status in ("Rejected", "Closed", "Settled"):
		return
	claim_doc.status = "Rejected"
	if meta.has_field("decision"):
		claim_doc.decision = "Reject"
	if meta.has_field("rejection_reason") and not claim_doc.get("rejection_reason"):
		claim_doc.rejection_reason = remarks or _("Auto-rejected by eligibility engine")


def _log_override_comment(claim_doc):
	if not claim_doc.get("name") or getattr(claim_doc.flags, "eligibility_override_logged", False):
		return
	try:
		claim_doc.add_comment(
			"Comment",
			_("Eligibility override by {0}: {1}").format(
				frappe.session.user, claim_doc.get("eligibility_override_reason") or ""
			),
		)
		claim_doc.flags.eligibility_override_logged = True
	except Exception:
		pass


def _write_evaluation_log(claim_doc, policy, result):
	if not frappe.db.exists("DocType", "Claim Eligibility Evaluation"):
		return None
	existing = frappe.db.get_value("Claim Eligibility Evaluation", {"insurance_claim": claim_doc.name}, "name")
	values = {
		"doctype": "Claim Eligibility Evaluation",
		"insurance_claim": claim_doc.name,
		"insurance_policy": claim_doc.get("policy") or (policy.name if policy else None),
		"evaluation_datetime": now_datetime(),
		"overall_score": result.overall_score,
		"overall_status": result.overall_status,
		"can_submit": 1 if result.can_submit else 0,
		"evaluated_by": frappe.session.user,
		"override_reason": claim_doc.get("eligibility_override_reason"),
		"overridden_by": frappe.session.user if claim_doc.get("eligibility_overridden") else None,
		"criteria_results": result.criteria_results,
	}
	if existing:
		doc = frappe.get_doc("Claim Eligibility Evaluation", existing)
		doc.update({k: v for k, v in values.items() if k != "doctype"})
		doc.set("criteria_results", [])
		for row in result.criteria_results:
			doc.append("criteria_results", row)
		doc.save(ignore_permissions=True)
		return doc.name
	doc = frappe.get_doc(values)
	doc.insert(ignore_permissions=True)
	return doc.name


def evaluate_policy_eligibility(policy_doc, throw=True):
	result = EligibilityResult()
	if isinstance(policy_doc, str):
		policy_doc = frappe.get_doc("Insurance Policy", policy_doc)
	if not _engine_enabled():
		result.overall_status = "Eligible"
		result.can_submit = True
		result.overall_score = 100
		return result
	client = None
	scheme = None
	if policy_doc.get("client") and frappe.db.exists("Insurance Client", policy_doc.client):
		client = frappe.get_doc("Insurance Client", policy_doc.client)
	if policy_doc.get("scheme") and frappe.db.exists("Insurance Scheme", policy_doc.scheme):
		scheme = frappe.get_doc("Insurance Scheme", policy_doc.scheme)
	claim_proxy = frappe._dict({
		"doctype": "Insurance Claim",
		"name": None,
		"policy": policy_doc.name,
		"client": policy_doc.get("client"),
		"scheme": policy_doc.get("scheme"),
		"provider": policy_doc.get("provider"),
		"claim_type": "All",
		"incident_date": policy_doc.get("start_date"),
		"claimed_amount": 0,
		"status": "Draft",
		"claim_documents": [],
		"compliance_checklist": [],
		"description": "",
		"claimant": None,
		"hospital": None,
		"reported_date": None,
		"submission_date": None,
		"flags": frappe._dict(ignore_eligibility=False),
	})
	criteria_list = get_applicable_criteria(
		scheme=policy_doc.get("scheme"),
		claim_type="All",
		provider=policy_doc.get("provider"),
		evaluation_stage="Policy Issuance",
	)
	settings = _settings()
	weights = _normalize_weights(criteria_list, cint(settings.get("normalize_weightage")))
	score = 0.0
	for criteria in criteria_list:
		passed, remarks = _evaluate_one(criteria, claim_proxy, policy_doc, client, scheme)
		weight = flt(weights.get(criteria.name))
		status = "Pass"
		contribution = 0.0
		if passed == "error":
			status = "Error"
			if criteria.is_mandatory:
				result.failed_mandatory.append(criteria)
		elif passed:
			contribution = weight
			score += contribution
		else:
			status = "Fail"
			if criteria.is_mandatory:
				result.failed_mandatory.append(criteria)
			if criteria.failure_action in ("Block Submission", "Auto-Reject"):
				result.block_messages.append(_("{0} – {1}").format(criteria.criteria_name, remarks or _("not met")))
		result.criteria_results.append({
			"eligibility_criteria": criteria.name,
			"criteria_code": criteria.get("criteria_code"),
			"criteria_version": cint(criteria.get("criteria_version") or 1),
			"is_mandatory": 1 if criteria.is_mandatory else 0,
			"weightage": weight,
			"result": status,
			"score_contribution": contribution,
			"remarks": remarks,
		})
	result.overall_score = flt(score, 2)
	if result.block_messages:
		result.overall_status = "Not Eligible"
		result.can_submit = False
	elif result.failed_mandatory:
		result.overall_status = "Conditionally Eligible"
		result.can_submit = False
	else:
		result.overall_status = "Eligible"
		result.can_submit = True
	if throw and not result.can_submit and not getattr(policy_doc.flags, "ignore_eligibility", False):
		frappe.throw(
			_("Policy is not eligible for issuance:<br>{0}").format("<br>".join(result.block_messages or [_("Mandatory eligibility criteria failed.")])),
			title=_("Eligibility Check Failed"),
		)
	return result


@frappe.whitelist()
def evaluate_claim_eligibility_api(claim_name, throw=0):
	return _result_as_dict(evaluate_claim_eligibility(claim_name, throw=cint(throw)))


@frappe.whitelist()
def get_applicable_criteria_api(scheme=None, claim_type=None, provider=None, evaluation_stage="Claim Intake"):
	return get_applicable_criteria(scheme=scheme, claim_type=claim_type, provider=provider, evaluation_stage=evaluation_stage)


@frappe.whitelist()
def recalculate_score(claim_name):
	result = evaluate_claim_eligibility(claim_name, throw=False)
	claim = frappe.get_doc("Insurance Claim", claim_name)
	_apply_score_to_claim(claim, result)
	if claim.meta.has_field("eligibility_score"):
		claim.db_set("eligibility_score", result.overall_score, update_modified=False)
		claim.db_set("eligibility_status", result.overall_status, update_modified=False)
		claim.db_set("eligibility_can_submit", 1 if result.can_submit else 0, update_modified=False)
	return _result_as_dict(result)


def _apply_score_to_claim(claim, result):
	if claim.meta.has_field("eligibility_score"):
		claim.eligibility_score = result.overall_score
	if claim.meta.has_field("eligibility_status"):
		claim.eligibility_status = result.overall_status
	if claim.meta.has_field("eligibility_can_submit"):
		claim.eligibility_can_submit = 1 if result.can_submit else 0


def _result_as_dict(result):
	return {
		"overall_score": result.overall_score,
		"overall_status": result.overall_status,
		"can_submit": result.can_submit,
		"criteria_results": result.criteria_results,
		"evaluation_name": result.evaluation_name,
		"warnings": result.warnings,
		"block_messages": result.block_messages,
	}


def evaluate_on_claim_validate(doc, method=None):
	if not _engine_enabled():
		return
	if getattr(doc.flags, "ignore_eligibility", False):
		return
	if doc.status in ("Settled", "Closed", "Rejected"):
		return
	changed = doc.is_new() or doc.has_value_changed("claimed_amount") or doc.has_value_changed("incident_date") or doc.has_value_changed("claim_type") or doc.has_value_changed("policy")
	submitting = doc.status in ("Submitted", "Under Review") and (doc.is_new() or doc.has_value_changed("status"))
	if not (changed or submitting):
		return
	should_throw = submitting or doc.status not in ("Draft",)
	result = evaluate_claim_eligibility(doc, throw=should_throw)
	_apply_score_to_claim(doc, result)
	if result.warnings and not should_throw:
		frappe.msgprint("<br>".join(result.warnings), title=_("Eligibility Warnings"), indicator="orange")


def rescore_open_claims():
	if not _engine_enabled():
		return
	if not frappe.db.exists("DocType", "Insurance Claim"):
		return
	claims = frappe.get_all(
		"Insurance Claim",
		filters={"status": ["in", ["Draft", "Submitted", "Under Review", "Documents Pending", "Additional Info Required"]]},
		pluck="name",
	)
	for name in claims:
		try:
			evaluate_claim_eligibility(name, throw=False)
		except Exception:
			frappe.log_error(title="Eligibility rescore failed", message=name)
