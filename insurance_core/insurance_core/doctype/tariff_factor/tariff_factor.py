import frappe
from frappe.model.document import Document


class TariffFactor(Document):
	def validate(self):
		if self.factor_code:
			# Normalise slug to lowercase underscore
			self.factor_code = self.factor_code.strip().lower().replace(" ", "_")
