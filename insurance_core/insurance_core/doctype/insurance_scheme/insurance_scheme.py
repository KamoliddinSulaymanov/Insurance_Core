import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from insurance_core.premium import calculate_premium as _calculate_premium


class InsuranceScheme(Document):
	def validate(self):
		self.set_missing_values()
		self.validate_ages()
		self.validate_sum_assured()

	def set_missing_values(self):
		if not self.scheme_code and self.scheme_id:
			self.scheme_code = self.scheme_id
		if self.grace_period_days is None:
			self.grace_period_days = 30
		if self.policy_term_months is None:
			self.policy_term_months = 12
		if self.status is None:
			self.status = "Draft"

	def validate_ages(self):
		if self.minimum_age and self.maximum_age and cint(self.minimum_age) > cint(self.maximum_age):
			frappe.throw(_("Minimum age cannot be greater than maximum age."), title=_("Invalid Age Range"))

	def validate_sum_assured(self):
		if (
			self.minimum_sum_assured
			and self.maximum_sum_assured
			and self.minimum_sum_assured > self.maximum_sum_assured
		):
			frappe.throw(
				_("Minimum sum assured cannot be greater than maximum sum assured."),
				title=_("Invalid Sum Assured"),
			)

	def calculate_premium(self, age=None, sum_insured=None, members=1, extras=None):
		return _calculate_premium(self, age=age, sum_insured=sum_insured, members=members, extras=extras)


@frappe.whitelist()
def get_schemes_by_provider(provider):
	return frappe.get_all(
		"Insurance Scheme",
		filters={"provider": provider, "status": "Active"},
		fields=["name", "scheme_name", "line_of_business", "policy_type", "status"],
	)


@frappe.whitelist(allow_guest=True)
def get_active_schemes(scheme_type=None):
	filters = {"status": ["in", ["Active", "Published"]]}
	if scheme_type:
		filters["line_of_business"] = scheme_type
	return frappe.get_all(
		"Insurance Scheme",
		filters=filters,
		fields=[
			"name",
			"scheme_id",
			"scheme_name",
			"provider",
			"line_of_business",
			"policy_type",
			"description",
			"minimum_sum_assured",
			"maximum_sum_assured",
		],
	)


@frappe.whitelist()
def calculate_premium(scheme, age=None, sum_insured=None, members=1, extras=None):
	import json

	if isinstance(extras, str):
		extras = json.loads(extras) if extras else {}
	return _calculate_premium(
		scheme,
		age=cint(age),
		sum_insured=sum_insured,
		members=cint(members) or 1,
		extras=extras or {},
	)
