# Copyright (c) 2026, Vivaswan Works and contributors
# License: MIT

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, getdate, flt, cstr


class PolicyUpload(Document):
	def validate(self):
		if self.policy_pdf and not str(self.policy_pdf).lower().endswith(".pdf"):
			frappe.throw(_("Only PDF files are supported for Policy Upload."))

		if self.client_mode == "Existing Client" and not self.existing_client:
			# Allow save while still drafting; enforce on create-policy action
			pass
		if self.client_mode == "Create New Client" and self.status in ("Parsed", "Client Linked"):
			if not self.new_client_name:
				frappe.throw(_("New Client Full Name is required when creating a new client."))

	def on_update(self):
		# Auto-fill new client name from extracted insured if empty
		if (
			self.client_mode == "Create New Client"
			and self.extracted_insured_name
			and not self.new_client_name
		):
			self.db_set("new_client_name", self.extracted_insured_name, update_modified=False)


@frappe.whitelist()
def parse_policy_pdf(name: str) -> dict:
	"""Extract text + structured fields from the attached policy PDF."""
	doc = frappe.get_doc("Policy Upload", name)
	if not doc.policy_pdf:
		frappe.throw(_("Please attach a Policy PDF first."))

	from insurance_core.policy_pdf_parser import parse_pdf_file

	file_doc = frappe.get_doc("File", {"file_url": doc.policy_pdf})
	file_path = file_doc.get_full_path()

	result = parse_pdf_file(file_path)

	doc.raw_extracted_text = result.get("raw_text") or ""
	doc.parse_log = result.get("log") or ""
	doc.extracted_policy_number = result.get("policy_number") or doc.extracted_policy_number
	doc.extracted_provider_name = result.get("provider_name") or doc.extracted_provider_name
	doc.extracted_scheme_name = result.get("scheme_name") or doc.extracted_scheme_name
	doc.extracted_sum_assured = result.get("sum_assured") or doc.extracted_sum_assured
	doc.extracted_premium = result.get("premium") or doc.extracted_premium
	doc.extracted_premium_frequency = result.get("premium_frequency") or doc.extracted_premium_frequency
	doc.extracted_start_date = result.get("start_date") or doc.extracted_start_date
	doc.extracted_end_date = result.get("end_date") or doc.extracted_end_date
	doc.extracted_issue_date = result.get("issue_date") or doc.extracted_issue_date
	doc.extracted_insured_name = result.get("insured_name") or doc.extracted_insured_name
	doc.extracted_terms_and_conditions = result.get("terms_and_conditions") or doc.extracted_terms_and_conditions
	doc.extracted_claim_eligibility = result.get("claim_eligibility") or doc.extracted_claim_eligibility
	doc.extracted_exclusions = result.get("exclusions") or doc.extracted_exclusions

	# Best-effort auto-map provider / scheme
	if doc.extracted_provider_name and not doc.provider:
		provider = _match_provider(doc.extracted_provider_name)
		if provider:
			doc.provider = provider
	if doc.extracted_scheme_name and not doc.scheme and doc.provider:
		scheme = _match_scheme(doc.extracted_scheme_name, doc.provider)
		if scheme:
			doc.scheme = scheme

	# Prefill new-client name
	if doc.client_mode == "Create New Client" and doc.extracted_insured_name and not doc.new_client_name:
		doc.new_client_name = doc.extracted_insured_name

	doc.status = "Parsed"
	doc.parse_status = result.get("message") or _("Parsed successfully. Review fields and create policy.")
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	return {
		"ok": True,
		"message": doc.parse_status,
		"fields": {
			"policy_number": doc.extracted_policy_number,
			"provider_name": doc.extracted_provider_name,
			"scheme_name": doc.extracted_scheme_name,
			"sum_assured": doc.extracted_sum_assured,
			"premium": doc.extracted_premium,
			"insured_name": doc.extracted_insured_name,
		},
	}


@frappe.whitelist()
def create_client_and_policy(name: str) -> dict:
	"""Create or link client, then create Insurance Policy from extracted data."""
	doc = frappe.get_doc("Policy Upload", name)

	if not doc.policy_pdf:
		frappe.throw(_("Policy PDF is required."))
	if not doc.extracted_policy_number:
		frappe.throw(_("Policy Number is required. Parse the PDF or enter it manually."))
	if not doc.provider:
		frappe.throw(_("Please select Insurance Provider (map from extracted name)."))
	if not doc.scheme:
		frappe.throw(_("Please select Insurance Scheme (map from extracted product name)."))
	if not doc.extracted_sum_assured:
		frappe.throw(_("Sum Assured is required."))
	if not doc.extracted_premium:
		frappe.throw(_("Premium Amount is required."))
	if not doc.extracted_start_date or not doc.extracted_end_date:
		frappe.throw(_("Start Date and End Date are required."))

	# Resolve client
	client_name = None
	if doc.client_mode == "Existing Client":
		if not doc.existing_client:
			frappe.throw(_("Select an Existing Client."))
		client_name = doc.existing_client
	else:
		client_name = _create_client_from_upload(doc)

	# Duplicate policy number guard
	if frappe.db.exists("Insurance Policy", {"policy_number": doc.extracted_policy_number}):
		frappe.throw(
			_("An Insurance Policy with number {0} already exists.").format(doc.extracted_policy_number)
		)

	renewal = doc.extracted_end_date
	policy = frappe.get_doc(
		{
			"doctype": "Insurance Policy",
			"policy_number": doc.extracted_policy_number,
			"client": client_name,
			"scheme": doc.scheme,
			"provider": doc.provider,
			"policy_type": doc.policy_type or "New Business",
			"coverage_level": doc.coverage_level or "Standard",
			"sum_assured": flt(doc.extracted_sum_assured),
			"premium_amount": flt(doc.extracted_premium),
			"premium_frequency": doc.extracted_premium_frequency or "Annually",
			"start_date": doc.extracted_start_date,
			"end_date": doc.extracted_end_date,
			"renewal_date": renewal,
			"issue_date": doc.extracted_issue_date or doc.extracted_start_date,
			"status": "Active",
			"agent": doc.agent,
			"payment_status": "Paid",
			"policy_document": doc.policy_pdf,
			# Custom fields (added by installer)
			"terms_and_conditions": doc.extracted_terms_and_conditions,
			"claim_eligibility_rules": doc.extracted_claim_eligibility,
			"policy_exclusions": doc.extracted_exclusions,
			"parsed_from_pdf": 1,
			"source_policy_upload": doc.name,
		}
	)

	# Optional primary member from insured name
	if doc.extracted_insured_name:
		policy.append(
			"policy_members",
			{
				"member_name": doc.extracted_insured_name,
				"relationship": "Self",
				"is_primary": 1,
				"date_of_birth": doc.new_client_dob if doc.client_mode == "Create New Client" else None,
			},
		)

	policy.insert(ignore_permissions=True)

	doc.created_client = client_name
	doc.created_policy = policy.name
	doc.status = "Policy Created"
	doc.parse_status = _("Policy {0} created for client {1}.").format(policy.name, client_name)
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	return {
		"ok": True,
		"client": client_name,
		"policy": policy.name,
		"message": doc.parse_status,
	}


def _create_client_from_upload(doc) -> str:
	full_name = (doc.new_client_name or doc.extracted_insured_name or "").strip()
	if not full_name:
		frappe.throw(_("New Client Full Name is required."))

	email = (doc.new_client_email or "").strip()
	# Unique client_id: use short name + timestamp fragment
	base = "".join(c for c in full_name.upper() if c.isalnum())[:8] or "CLT"
	client_id = f"{base}-{frappe.generate_hash(length=4).upper()}"

	# Avoid duplicate email if provided
	if email and frappe.db.exists("Insurance Client", {"email": email}):
		existing = frappe.db.get_value("Insurance Client", {"email": email}, "name")
		frappe.msgprint(
			_("Client with email {0} already exists ({1}). Linking to that client.").format(email, existing)
		)
		return existing

	client = frappe.get_doc(
		{
			"doctype": "Insurance Client",
			"client_id": client_id,
			"full_name": full_name,
			"client_type": "Individual",
			"email": email or f"{client_id.lower()}@placeholder.local",
			"phone": doc.new_client_phone,
			"date_of_birth": doc.new_client_dob,
			"address": doc.new_client_address,
			"lifecycle_stage": "Policyholder",
			"source": "Walk-in",
			"kyc_status": "Pending",
			"consent_data_processing": 1,
		}
	)
	client.insert(ignore_permissions=True)
	return client.name


def _match_provider(name: str) -> str | None:
	if not name:
		return None
	name = name.strip()
	# Exact
	val = frappe.db.get_value("Insurance Provider", {"provider_name": name}, "name")
	if val:
		return val
	# Fuzzy contains
	rows = frappe.get_all(
		"Insurance Provider",
		filters={"provider_name": ["like", f"%{name[:20]}%"]},
		fields=["name", "provider_name"],
		limit=5,
	)
	if len(rows) == 1:
		return rows[0].name
	# Try reverse: provider name contained in extracted
	all_p = frappe.get_all("Insurance Provider", fields=["name", "provider_name"], limit=100)
	for p in all_p:
		pn = (p.provider_name or "").lower()
		if pn and (pn in name.lower() or name.lower() in pn):
			return p.name
	return None


def _match_scheme(name: str, provider: str | None = None) -> str | None:
	if not name:
		return None
	filters = {"scheme_name": ["like", f"%{name[:30]}%"]}
	if provider:
		filters["provider"] = provider
	rows = frappe.get_all("Insurance Scheme", filters=filters, fields=["name"], limit=5)
	if len(rows) == 1:
		return rows[0].name
	# Exact scheme_name
	val = frappe.db.get_value("Insurance Scheme", {"scheme_name": name}, "name")
	return val
