# Copyright (c) 2026, Vivaswan Works and contributors
# License: MIT
"""
Add the Engineering Line of Business (vertical) across Insurance Core.

Run on site:
  bench --site <site> execute insurance_core.add_engineering_vertical.setup

Or from this artifacts copy after placing under insurance_core/:
  bench --site <site> execute insurance_core.add_engineering_vertical.setup

What it does:
  1. Extends Select options for line_of_business on:
       - Insurance Scheme (DocType JSON + Property Setter)
       - Insurance RFQ Detail
       - Insurer RFQ Rule
       - Insurance Opportunity (Custom Field if present)
  2. Does not delete existing data; only appends "Engineering" when missing.
  3. Optionally seeds sample Engineering schemes (idempotent) if demo providers exist.

Product lines under Engineering (stored in scheme.policy_type):
  - Contractors' All Risks (CAR)
  - Erection All Risks (EAR)
  - Advance Loss of Profits (ALOP / DSU)
  - Contractors' Plant and Machinery (CPM)
  - Machinery Breakdown (MB)
  - Civil Engineering Completed Risks (CECR)
"""

from __future__ import annotations

import frappe

LOB_OPTIONS = "Health\nAuto\nLife\nProperty\nTravel\nMarine\nLiability\nEngineering"

DOCTYPES_WITH_LOB = [
	"Insurance Scheme",
	"Insurance RFQ Detail",
	"Insurer RFQ Rule",
]


def _ensure_option(doctype: str, fieldname: str = "line_of_business") -> bool:
	"""Append Engineering to Select options if missing. Returns True if changed."""
	meta = frappe.get_meta(doctype)
	df = meta.get_field(fieldname)
	if not df:
		return False
	current = (df.options or "").strip()
	if "Engineering" in current.split("\n"):
		return False
	# Prefer canonical full list; fall back to append
	new_opts = LOB_OPTIONS if "Health" in current else (current + "\nEngineering").strip()
	# Property Setter so it survives migrate without rewriting JSON every time
	ps_name = frappe.db.get_value(
		"Property Setter",
		{"doc_type": doctype, "field_name": fieldname, "property": "options"},
		"name",
	)
	if ps_name:
		frappe.db.set_value("Property Setter", ps_name, "value", new_opts)
	else:
		ps = frappe.get_doc(
			{
				"doctype": "Property Setter",
				"doctype_or_field": "DocField",
				"doc_type": doctype,
				"field_name": fieldname,
				"property": "options",
				"property_type": "Text",
				"value": new_opts,
			}
		)
		ps.insert(ignore_permissions=True)
	# Also update the DocField in the DocType itself for consistency
	frappe.db.sql(
		"""
		UPDATE `tabDocField`
		SET options = %s
		WHERE parent = %s AND fieldname = %s
		""",
		(new_opts, doctype, fieldname),
	)
	return True


def _ensure_custom_field_opportunity() -> bool:
	"""Update Insurance Opportunity custom field options if it exists."""
	name = frappe.db.get_value(
		"Custom Field",
		{"dt": "Insurance Opportunity", "fieldname": "line_of_business"},
		"name",
	)
	if not name:
		return False
	opts = frappe.db.get_value("Custom Field", name, "options") or ""
	if "Engineering" in opts.split("\n"):
		return False
	frappe.db.set_value("Custom Field", name, "options", LOB_OPTIONS)
	return True


def _seed_engineering_schemes() -> int:
	"""Insert sample Engineering schemes if providers exist. Idempotent."""
	providers = {
		"PROV-NIA": frappe.db.get_value("Insurance Provider", {"provider_id": "PROV-NIA"}, "name"),
		"PROV-BAJAJ": frappe.db.get_value("Insurance Provider", {"provider_id": "PROV-BAJAJ"}, "name"),
	}
	if not any(providers.values()):
		return 0

	rows = [
		{
			"scheme_id": "SCH-NIA-ENG-CAR",
			"scheme_code": "NIA-ENG-CAR",
			"scheme_name": "New India Contractors' All Risks",
			"provider_key": "PROV-NIA",
			"policy_type": "Contractors' All Risks (CAR)",
			"minimum_sum_assured": 1_000_000,
			"maximum_sum_assured": 5_000_000_000,
			"renewal_allowed": 0,
		},
		{
			"scheme_id": "SCH-BAJAJ-ENG-EAR",
			"scheme_code": "BAJAJ-ENG-EAR",
			"scheme_name": "Bajaj Allianz Erection All Risks",
			"provider_key": "PROV-BAJAJ",
			"policy_type": "Erection All Risks (EAR)",
			"minimum_sum_assured": 1_000_000,
			"maximum_sum_assured": 5_000_000_000,
			"renewal_allowed": 0,
		},
		{
			"scheme_id": "SCH-NIA-ENG-ALOP",
			"scheme_code": "NIA-ENG-ALOP",
			"scheme_name": "New India Advance Loss of Profits (ALOP)",
			"provider_key": "PROV-NIA",
			"policy_type": "Advance Loss of Profits (ALOP / DSU)",
			"minimum_sum_assured": 5_000_000,
			"maximum_sum_assured": 2_000_000_000,
			"renewal_allowed": 0,
		},
		{
			"scheme_id": "SCH-BAJAJ-ENG-CPM",
			"scheme_code": "BAJAJ-ENG-CPM",
			"scheme_name": "Bajaj Allianz Contractors' Plant & Machinery",
			"provider_key": "PROV-BAJAJ",
			"policy_type": "Contractors' Plant and Machinery (CPM)",
			"minimum_sum_assured": 500_000,
			"maximum_sum_assured": 500_000_000,
			"renewal_allowed": 1,
		},
		{
			"scheme_id": "SCH-NIA-ENG-MB",
			"scheme_code": "NIA-ENG-MB",
			"scheme_name": "New India Machinery Breakdown",
			"provider_key": "PROV-NIA",
			"policy_type": "Machinery Breakdown (MB)",
			"minimum_sum_assured": 1_000_000,
			"maximum_sum_assured": 1_000_000_000,
			"renewal_allowed": 1,
		},
		{
			"scheme_id": "SCH-BAJAJ-ENG-CECR",
			"scheme_code": "BAJAJ-ENG-CECR",
			"scheme_name": "Bajaj Allianz Civil Engineering Completed Risks",
			"provider_key": "PROV-BAJAJ",
			"policy_type": "Civil Engineering Completed Risks (CECR)",
			"minimum_sum_assured": 5_000_000,
			"maximum_sum_assured": 2_000_000_000,
			"renewal_allowed": 1,
		},
	]

	created = 0
	for row in rows:
		if frappe.db.exists("Insurance Scheme", {"scheme_id": row["scheme_id"]}):
			continue
		prov = providers.get(row["provider_key"])
		if not prov:
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Insurance Scheme",
				"scheme_id": row["scheme_id"],
				"scheme_code": row["scheme_code"],
				"scheme_name": row["scheme_name"],
				"provider": prov,
				"line_of_business": "Engineering",
				"policy_type": row["policy_type"],
				"product_category": "Corporate",
				"status": "Active",
				"coverage_type": "Indemnity",
				"claim_process_type": "Reimbursement",
				"premium_basis": "Sum Insured",
				"premium_frequency": "Annually",
				"gst_applicable": 1,
				"tax_gst_rate": 18,
				"policy_term_months": 12,
				"grace_period_days": 30,
				"waiting_period_days": 0,
				"minimum_sum_assured": row["minimum_sum_assured"],
				"maximum_sum_assured": row["maximum_sum_assured"],
				"sum_insured_type": "Fixed",
				"renewal_allowed": row["renewal_allowed"],
				"target_audience": "SMEs",
			}
		)
		doc.insert(ignore_permissions=True)
		created += 1
	return created


def setup(seed_schemes: bool = True):
	"""Main entry: extend LOB options + optionally seed schemes."""
	changed = []
	for dt in DOCTYPES_WITH_LOB:
		if frappe.db.exists("DocType", dt) and _ensure_option(dt):
			changed.append(dt)
	if _ensure_custom_field_opportunity():
		changed.append("Insurance Opportunity (Custom Field)")

	frappe.clear_cache()
	created = _seed_engineering_schemes() if seed_schemes else 0
	frappe.db.commit()

	msg = (
		f"Engineering vertical ready. Updated LOB options on: {', '.join(changed) or 'already present'}. "
		f"Seeded {created} Engineering scheme(s)."
	)
	print(msg)
	return {"updated": changed, "schemes_created": created, "message": msg}
