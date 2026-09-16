# Copyright (c) 2026, Vivaswan Works and contributors
# License: MIT

"""
Broker RFQ helpers – works WITH standard ERPNext Request for Quotation
and Supplier Quotation without modifying those core doctypes.

Architecture
------------
- ERPNext RFQ / Supplier Quotation remain untouched.
- Insurance RFQ Detail (1:1 with RFQ) holds insurance-specific data.
- Insurance RFQ Insurer (child) tracks invited insurers + links to quotes.
- Insurer RFQ Rule drives automatic selection of 4–5 insurers.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, now_datetime, nowdate, today


# ---------------------------------------------------------------------------
# Insurer selection (rule engine)
# ---------------------------------------------------------------------------

def get_matching_insurers(
	line_of_business: str,
	sum_insured: float | None = None,
	age: int | None = None,
	client_type: str | None = None,
	max_count: int = 5,
) -> list[dict]:
	"""
	Return list of dicts [{provider, supplier, priority}, ...] that match
	the given criteria, ordered by priority (lowest first), limited to max_count.
	"""
	if not line_of_business:
		frappe.throw(_("Line of Business is required to select insurers."), title=_("Missing LOB"))

	rules = frappe.get_all(
		"Insurer RFQ Rule",
		filters={"is_active": 1, "line_of_business": line_of_business},
		fields=[
			"name",
			"insurance_provider",
			"priority",
			"min_sum_insured",
			"max_sum_insured",
			"min_age",
			"max_age",
			"client_types",
			"require_active_agreement",
			"valid_from",
			"valid_to",
			"min_claim_settlement_ratio",
		],
		order_by="priority asc",
	)

	matched: list[dict] = []
	seen: set[str] = set()
	today_date = getdate(today())

	for rule in rules:
		provider = rule.insurance_provider
		if not provider or provider in seen:
			continue

		# Validity window
		if rule.valid_from and getdate(rule.valid_from) > today_date:
			continue
		if rule.valid_to and getdate(rule.valid_to) < today_date:
			continue

		# Sum insured band
		if sum_insured is not None:
			if rule.min_sum_insured and flt(sum_insured) < flt(rule.min_sum_insured):
				continue
			if rule.max_sum_insured and flt(sum_insured) > flt(rule.max_sum_insured):
				continue

		# Age band
		if age is not None:
			if rule.min_age and cint(age) < cint(rule.min_age):
				continue
			if rule.max_age and cint(age) > cint(rule.max_age):
				continue

		# Client type (comma-separated free text)
		if client_type and rule.client_types:
			allowed = [c.strip().lower() for c in rule.client_types.split(",") if c.strip()]
			if allowed and client_type.strip().lower() not in allowed:
				continue

		# Active agreement on provider
		if rule.require_active_agreement and not _provider_has_active_agreement(provider):
			continue

		# Optional quality filter
		if rule.min_claim_settlement_ratio:
			csr = frappe.db.get_value("Insurance Provider", provider, "claim_settlement_ratio")
			if csr is not None and flt(csr) < flt(rule.min_claim_settlement_ratio):
				continue

		supplier = _get_supplier_for_provider(provider)
		matched.append({
			"provider": provider,
			"supplier": supplier,
			"priority": rule.priority,
		})
		seen.add(provider)

		if len(matched) >= max_count:
			break

	return matched


def _provider_has_active_agreement(provider: str) -> bool:
	row = frappe.db.get_value(
		"Insurance Provider",
		provider,
		["status", "contract_start_date", "contract_end_date", "agreement_start", "agreement_end"],
		as_dict=True,
	)
	if not row or row.status != "Active":
		return False

	today_date = getdate(today())
	start = row.contract_start_date or row.agreement_start
	end = row.contract_end_date or row.agreement_end

	if start and getdate(start) > today_date:
		return False
	if end and getdate(end) < today_date:
		return False
	return True


def _get_supplier_for_provider(provider: str) -> str | None:
	"""
	Return ERPNext Supplier linked via our field on Insurance Provider.
	(Insurance Provider is our doctype – safe to have erpnext_supplier.)
	"""
	return frappe.db.get_value("Insurance Provider", provider, "erpnext_supplier")
