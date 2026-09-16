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


# ---------------------------------------------------------------------------
# Create RFQ from Opportunity (creates both ERPNext RFQ + our Detail)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def create_rfq_from_opportunity(opportunity: str, max_insurers: int = 5) -> dict:
	"""
	1. Create standard ERPNext Request for Quotation (untouched core).
	2. Create Insurance RFQ Detail linked 1:1.
	3. Run rule engine and populate both the ERPNext suppliers table
	   and our child table Insurance RFQ Insurer.
	Returns {"rfq": <erpnext rfq name>, "detail": <our detail name>}
	"""
	opp = frappe.get_doc("Insurance Opportunity", opportunity)

	line_of_business = getattr(opp, "line_of_business", None)
	if not line_of_business and opp.insurance_scheme:
		line_of_business = frappe.db.get_value(
			"Insurance Scheme", opp.insurance_scheme, "line_of_business"
		)

	if not line_of_business:
		frappe.throw(
			_("Set Line of Business (or Interested Scheme) on the Opportunity first."),
			title=_("Missing Line of Business"),
		)

	sum_insured = flt(getattr(opp, "required_sum_insured", None) or opp.expected_premium)
	age = cint(getattr(opp, "proposer_age", None))
	client_type = getattr(opp, "client_type", None)
	max_insurers = cint(max_insurers) or 5

	providers = get_matching_insurers(
		line_of_business=line_of_business,
		sum_insured=sum_insured or None,
		age=age or None,
		client_type=client_type,
		max_count=max_insurers,
	)

	if not providers:
		frappe.throw(
			_("No active insurers match the current criteria. Check Insurer RFQ Rules."),
			title=_("No Matching Insurers"),
		)

	# ----- 1. Create standard ERPNext RFQ (core remains pristine) -----
	company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
		"Global Defaults", "default_company"
	)
	if not company:
		frappe.throw(_("Set a default Company before creating an RFQ."), title=_("Missing Company"))

	rfq = frappe.new_doc("Request for Quotation")
	rfq.transaction_date = nowdate()
	rfq.company = company
	rfq.message_for_supplier = (
		f"Request for Quotation – {line_of_business}\n"
		f"Client: {opp.party or opp.client or ''}\n"
		f"Required Sum Insured: {sum_insured}\n"
		f"Please submit your quote with premium, key terms and validity."
	)

	# Add suppliers that have a linked Supplier record
	for p in providers:
		if not p.get("supplier"):
			frappe.msgprint(
				_("Insurance Provider {0} has no linked ERPNext Supplier – skipped on core RFQ.").format(
					frappe.bold(p["provider"])
				),
				indicator="orange",
				alert=True,
			)
			continue
		rfq.append(
			"suppliers",
			{
				"supplier": p["supplier"],
				"email_id": frappe.db.get_value("Supplier", p["supplier"], "email_id")
				or frappe.db.get_value("Insurance Provider", p["provider"], "general_email"),
				"send_email": 1,
			},
		)

	# Minimal item so RFQ validates (insurance is not a stock item)
	rfq.append(
		"items",
		{
			"item_code": _get_or_create_insurance_item(),
			"qty": 1,
			"schedule_date": nowdate(),
			"description": f"{line_of_business} – Sum Insured {sum_insured}",
		},
	)

	if not rfq.suppliers:
		frappe.throw(
			_("None of the matched insurers have a linked Supplier. "
			  "Set Insurance Provider → ERPNext Supplier first."),
			title=_("No Suppliers"),
		)

	rfq.insert(ignore_permissions=True)

	# ----- 2. Create our Insurance RFQ Detail (1:1) -----
	detail = frappe.new_doc("Insurance RFQ Detail")
	detail.request_for_quotation = rfq.name
	detail.opportunity = opp.name
	detail.client = opp.client
	detail.line_of_business = line_of_business
	detail.required_sum_insured = sum_insured
	detail.proposer_age = age
	detail.client_type = client_type
	detail.max_insurers = max_insurers
	detail.status = "Draft"
	detail.risk_summary = getattr(opp, "notes", None) or ""

	for p in providers:
		detail.append(
			"insurers",
			{
				"insurance_provider": p["provider"],
				"supplier": p.get("supplier"),
				"status": "Invited",
				"invited_on": now_datetime(),
			},
		)

	detail.insert(ignore_permissions=True)

	# Link back on Opportunity (our doctype – safe)
	if frappe.get_meta("Insurance Opportunity").has_field("insurance_rfq_detail"):
		opp.db_set("insurance_rfq_detail", detail.name)
	if frappe.get_meta("Insurance Opportunity").has_field("rfq"):
		opp.db_set("rfq", rfq.name)
	opp.db_set("stage", "Quote Sent")

	frappe.msgprint(
		_("RFQ {0} + Insurance Detail {1} created with {2} insurer(s).").format(
			frappe.bold(rfq.name), frappe.bold(detail.name), len(detail.insurers)
		),
		indicator="green",
		alert=True,
	)
	return {"rfq": rfq.name, "detail": detail.name}


@frappe.whitelist()
def select_insurers_on_detail(detail_name: str, max_insurers: int = 5) -> dict:
	"""
	Re-run rule engine on an existing Insurance RFQ Detail and
	repopulate both our child table and the linked ERPNext RFQ suppliers.
	"""
	detail = frappe.get_doc("Insurance RFQ Detail", detail_name)
	if not detail.request_for_quotation:
		frappe.throw(_("This Detail has no linked ERPNext RFQ."), title=_("Missing RFQ"))

	line_of_business = detail.line_of_business
	sum_insured = flt(detail.required_sum_insured)
	age = cint(detail.proposer_age)
	client_type = detail.client_type
	max_insurers = cint(max_insurers) or cint(detail.max_insurers) or 5

	if not line_of_business:
		frappe.throw(_("Set Line of Business on the Detail first."), title=_("Missing LOB"))

	providers = get_matching_insurers(
		line_of_business=line_of_business,
		sum_insured=sum_insured or None,
		age=age or None,
		client_type=client_type,
		max_count=max_insurers,
	)

	# Update our child table
	detail.set("insurers", [])
	for p in providers:
		detail.append(
			"insurers",
			{
				"insurance_provider": p["provider"],
				"supplier": p.get("supplier"),
				"status": "Invited",
				"invited_on": now_datetime(),
			},
		)
	detail.max_insurers = max_insurers
	detail.save(ignore_permissions=True)

	# Also update the core ERPNext RFQ suppliers table (no schema change)
	rfq = frappe.get_doc("Request for Quotation", detail.request_for_quotation)
	rfq.set("suppliers", [])
	for p in providers:
		if not p.get("supplier"):
			continue
		rfq.append(
			"suppliers",
			{
				"supplier": p["supplier"],
				"email_id": frappe.db.get_value("Supplier", p["supplier"], "email_id"),
				"send_email": 1,
			},
		)
	rfq.save(ignore_permissions=True)

	return {
		"detail": detail.name,
		"rfq": rfq.name,
		"insurers_added": len(detail.insurers),
		"providers": [p["provider"] for p in providers],
	}


def _get_or_create_insurance_item() -> str:
	item_code = "INSURANCE-COVER"
	if frappe.db.exists("Item", item_code):
		return item_code

	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": "Insurance Cover (RFQ)",
			"item_group": "Services",
			"stock_uom": "Nos",
			"is_stock_item": 0,
			"is_purchase_item": 1,
			"is_sales_item": 0,
			"description": "Placeholder item for insurance RFQs – do not delete",
		}
	)
	item.insert(ignore_permissions=True)
	return item_code


# ---------------------------------------------------------------------------
# Supplier Quotation submit → sync into our world
# ---------------------------------------------------------------------------

def on_supplier_quotation_submit(doc, method=None):
	"""
	doc_events handler (hooks.py).
	When a Supplier Quotation is submitted we:
	1. Find the linked Insurance RFQ Detail (via RFQ on the items)
	2. Create / update an Insurance Quotation
	3. Update the matching child row in Insurance RFQ Insurer
	"""
	if not doc.supplier:
		return

	# Resolve Insurance Provider from our mapping field
	provider = frappe.db.get_value(
		"Insurance Provider", {"erpnext_supplier": doc.supplier}, "name"
	)
	if not provider:
		return  # not an insurance-related quotation – ignore

	# Find RFQ name from items
	rfq_name = None
	for item in doc.items:
		if item.request_for_quotation:
			rfq_name = item.request_for_quotation
			break
	if not rfq_name:
		return

	detail_name = frappe.db.get_value(
		"Insurance RFQ Detail", {"request_for_quotation": rfq_name}, "name"
	)
	if not detail_name:
		return

	detail = frappe.get_doc("Insurance RFQ Detail", detail_name)

	# ----- Create / update Insurance Quotation -----
	existing = frappe.db.get_value(
		"Insurance Quotation",
		{"supplier_quotation": doc.name},
		"name",
	)

	net_premium = flt(doc.total)
	tax_amount = flt(doc.total_taxes_and_charges)
	total_premium = flt(doc.grand_total)
	sum_insured = flt(detail.required_sum_insured)
	validity = doc.valid_till

	if existing:
		qtn = frappe.get_doc("Insurance Quotation", existing)
	else:
		qtn = frappe.new_doc("Insurance Quotation")
		qtn.quotation_number = f"QTN-{doc.name}"
		if frappe.get_meta("Insurance Quotation").has_field("supplier_quotation"):
			qtn.supplier_quotation = doc.name
		if frappe.get_meta("Insurance Quotation").has_field("insurance_rfq_detail"):
			qtn.insurance_rfq_detail = detail.name

	qtn.client = detail.client
	qtn.provider = provider
	qtn.sum_insured = sum_insured
	qtn.net_premium = net_premium
	qtn.tax_amount = tax_amount
	qtn.total_premium = total_premium
	qtn.valid_upto = validity
	qtn.status = "Sent"
	if not qtn.age:
		qtn.age = detail.proposer_age or 35

	qtn.flags.ignore_mandatory = True  # scheme may still be empty at this stage
	if existing:
		qtn.save(ignore_permissions=True)
	else:
		qtn.insert(ignore_permissions=True)

	# ----- Update child row -----
	updated = False
	for row in detail.insurers:
		if row.insurance_provider == provider or row.supplier == doc.supplier:
			row.status = "Quote Received"
			row.supplier_quotation = doc.name
			row.insurance_quotation = qtn.name
			row.responded_on = now_datetime()
			updated = True
			break

	if not updated:
		# Insurer was not in the original selection – still record it
		detail.append(
			"insurers",
			{
				"insurance_provider": provider,
				"supplier": doc.supplier,
				"status": "Quote Received",
				"supplier_quotation": doc.name,
				"insurance_quotation": qtn.name,
				"responded_on": now_datetime(),
			},
		)

	# Bump parent status if any quotes arrived
	if detail.status in ("Draft", "Sent"):
		detail.status = "Quotes Received"

	detail.save(ignore_permissions=True)
	return qtn.name


# ---------------------------------------------------------------------------
# Select winning quote
# ---------------------------------------------------------------------------

@frappe.whitelist()
def select_winning_quote(insurance_quotation: str) -> str:
	"""
	Mark an Insurance Quotation as the winner.
	Updates Detail, child row, Opportunity stage.
	"""
	qtn = frappe.get_doc("Insurance Quotation", insurance_quotation)

	detail_name = None
	if frappe.get_meta("Insurance Quotation").has_field("insurance_rfq_detail"):
		detail_name = qtn.get("insurance_rfq_detail")

	if not detail_name and frappe.get_meta("Insurance Quotation").has_field("supplier_quotation"):
		# fallback via Supplier Quotation → RFQ → Detail
		sq = qtn.get("supplier_quotation")
		if sq:
			rfq = frappe.db.get_value(
				"Supplier Quotation Item",
				{"parent": sq},
				"request_for_quotation",
			)
			if rfq:
				detail_name = frappe.db.get_value(
					"Insurance RFQ Detail", {"request_for_quotation": rfq}, "name"
				)

	if detail_name:
		detail = frappe.get_doc("Insurance RFQ Detail", detail_name)
		detail.selected_quotation = qtn.name
		detail.status = "Closed"

		for row in detail.insurers:
			if row.insurance_quotation == qtn.name:
				row.status = "Selected"
			elif row.status == "Selected":
				row.status = "Quote Received"  # clear previous winner

		detail.save(ignore_permissions=True)

		# Advance Opportunity
		if detail.opportunity:
			frappe.db.set_value("Insurance Opportunity", detail.opportunity, "stage", "Won")
			if frappe.get_meta("Insurance Opportunity").has_field("converted_quotation"):
				frappe.db.set_value(
					"Insurance Opportunity",
					detail.opportunity,
					"converted_quotation",
					qtn.name,
				)

	# Mark quotation itself
	qtn.db_set("status", "Accepted")
	if frappe.get_meta("Insurance Quotation").has_field("is_selected"):
		qtn.db_set("is_selected", 1)

	frappe.msgprint(
		_("Quotation {0} marked as selected.").format(frappe.bold(qtn.name)),
		indicator="green",
		alert=True,
	)
	return qtn.name
