import json

import frappe
from frappe.utils import cint


@frappe.whitelist()
def check_app_permission():
	return bool(
		set(frappe.get_roles())
		& {
			"System Manager",
			"Insurance Manager",
			"Insurance Agent",
			"Claims Adjuster",
			"Compliance Officer",
			"Insurance User",
		}
	)


@frappe.whitelist()
def ping():
	return {"ok": True, "user": frappe.session.user, "roles": frappe.get_roles()}


@frappe.whitelist()
def calculate_premium(scheme, age=None, sum_insured=None, members=1, extras=None):
	from insurance_core.premium import calculate_premium as _calc

	if isinstance(extras, str):
		extras = json.loads(extras) if extras else {}
	return _calc(
		scheme,
		age=cint(age),
		sum_insured=sum_insured,
		members=cint(members) or 1,
		extras=extras or {},
	)


@frappe.whitelist()
def get_active_providers():
	from insurance_core.insurance_core.doctype.insurance_provider.insurance_provider import (
		get_active_providers as _fn,
	)

	return _fn()


@frappe.whitelist(allow_guest=True)
def get_active_schemes(scheme_type=None):
	from insurance_core.insurance_core.doctype.insurance_scheme.insurance_scheme import (
		get_active_schemes as _fn,
	)

	return _fn(scheme_type=scheme_type)


@frappe.whitelist()
def convert_quotation(quotation):
	from insurance_core.insurance_core.doctype.insurance_quotation.insurance_quotation import convert_to_policy

	return convert_to_policy(quotation)


@frappe.whitelist()
def create_renewal(policy):
	from insurance_core.insurance_core.doctype.insurance_policy.insurance_policy import create_renewal as _fn

	return _fn(policy)


@frappe.whitelist()
def apply_endorsement(name):
	from insurance_core.insurance_core.doctype.policy_endorsement.policy_endorsement import (
		apply_endorsement as _fn,
	)

	return _fn(name)


@frappe.whitelist()
def approve_endorsement(name):
	from insurance_core.insurance_core.doctype.policy_endorsement.policy_endorsement import (
		approve_endorsement as _fn,
	)

	return _fn(name)


@frappe.whitelist()
def reject_endorsement(name, reason=None):
	from insurance_core.insurance_core.doctype.policy_endorsement.policy_endorsement import (
		reject_endorsement as _fn,
	)

	return _fn(name, reason=reason)


@frappe.whitelist()
def estimate_endorsement_impact(policy, endorsement_type, new_value=None, effective_date=None):
	from insurance_core.insurance_core.doctype.policy_endorsement.policy_endorsement import estimate_impact

	return estimate_impact(policy, endorsement_type, new_value=new_value, effective_date=effective_date)


@frappe.whitelist()
def evaluate_claim_eligibility(claim_name):
	from insurance_core.eligibility import evaluate_claim_eligibility_api

	return evaluate_claim_eligibility_api(claim_name, throw=0)


@frappe.whitelist()
def get_applicable_criteria(scheme=None, claim_type=None, provider=None):
	from insurance_core.eligibility import get_applicable_criteria_api

	return get_applicable_criteria_api(scheme=scheme, claim_type=claim_type, provider=provider)


@frappe.whitelist()
def recalculate_score(claim_name):
	from insurance_core.eligibility import recalculate_score as _fn

	return _fn(claim_name)


@frappe.whitelist()
def accrue_commission(policy, event="Issue"):
	from insurance_core.commission import accrue_for_policy

	return accrue_for_policy(policy, event=event)


@frappe.whitelist()
def approve_commission_payout(name):
	from insurance_core.commission import approve_payout

	return approve_payout(name)


@frappe.whitelist()
def mark_commission_paid(name, payout_date=None, reference=None):
	from insurance_core.commission import mark_payout_paid

	return mark_payout_paid(name, payout_date=payout_date, reference=reference)


@frappe.whitelist()
def get_print_html(doctype, name, template_key=None):
	from insurance_core.print_formats import get_print_html as _fn

	return _fn(doctype, name, template_key=template_key)
