import frappe
from frappe.model.document import Document
from frappe.utils import flt


class PartnerCreditAccount(Document):
	def validate(self):
		self.update_available_balance()

	def update_available_balance(self):
		credit = flt(self.sanctioned_credit_limit)
		deposit = flt(self.deposit_balance)
		utilized = flt(self.utilized_limit)
		self.available_balance = credit + deposit - utilized
