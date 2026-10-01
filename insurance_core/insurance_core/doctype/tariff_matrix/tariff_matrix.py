import frappe
from frappe.model.document import Document


class TariffMatrix(Document):
	def validate(self):
		if self.matrix_code:
			self.matrix_code = self.matrix_code.strip().lower().replace(" ", "_")
