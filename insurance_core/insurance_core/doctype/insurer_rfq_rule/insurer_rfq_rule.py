# Copyright (c) 2026, Vivaswan Works and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today


class InsurerRFQRule(Document):
	def validate(self):
		self.validate_sum_insured_range()
		self.validate_age_range()
		self.validate_dates()

	def validate_sum_insured_range(self):
		if (
			self.min_sum_insured
			and self.max_sum_insured
			and self.min_sum_insured > self.max_sum_insured
		):
			frappe.throw(
				_("Minimum Sum Insured cannot be greater than Maximum Sum Insured."),
				title=_("Invalid Sum Insured Range"),
			)

	def validate_age_range(self):
		if self.min_age and self.max_age and self.min_age > self.max_age:
			frappe.throw(
				_("Minimum Age cannot be greater than Maximum Age."),
				title=_("Invalid Age Range"),
			)

	def validate_dates(self):
		if self.valid_from and self.valid_to and getdate(self.valid_from) > getdate(self.valid_to):
			frappe.throw(
				_("Rule Valid From cannot be after Valid To."),
				title=_("Invalid Validity"),
			)

	def is_currently_valid(self) -> bool:
		if not self.is_active:
			return False
		today_date = getdate(today())
		if self.valid_from and getdate(self.valid_from) > today_date:
			return False
		if self.valid_to and getdate(self.valid_to) < today_date:
			return False
		return True
