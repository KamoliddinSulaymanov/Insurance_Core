# Copyright (c) 2026, Vivaswan Works and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document


class InsuranceRFQDetail(Document):
	def validate(self):
		self.validate_unique_rfq_link()
		self.set_missing_values()

	def validate_unique_rfq_link(self):
		if not self.request_for_quotation:
			return
		existing = frappe.db.get_value(
			"Insurance RFQ Detail",
			{
				"request_for_quotation": self.request_for_quotation,
				"name": ["!=", self.name],
			},
			"name",
		)
		if existing:
			frappe.throw(
				_("ERPNext RFQ {0} is already linked to Insurance RFQ Detail {1}.").format(
					frappe.bold(self.request_for_quotation), frappe.bold(existing)
				),
				title=_("Duplicate Link"),
			)

	def set_missing_values(self):
		if self.opportunity and not self.client:
			self.client = frappe.db.get_value(
				"Insurance Opportunity", self.opportunity, "client"
			)
		if self.request_for_quotation and not self.opportunity:
			pass
