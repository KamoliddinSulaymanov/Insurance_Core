import ast
import frappe
from frappe import _
from frappe.model.document import Document


class ProductCalculationRule(Document):
	def validate(self):
		self.validate_formula()

	def validate_formula(self):
		if not self.formula:
			return

		# 1. Parse AST to verify it's a valid mathematical expression
		try:
			tree = ast.parse(self.formula, mode="eval")
		except Exception as e:
			frappe.throw(_("Invalid formula syntax: {0}").format(e))

		# 2. Extract variable names from formula
		formula_vars = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}

		# Built-in standard variables available in every calculation
		standard_vars = {
			"base_premium",
			"sum_insured",
			"members",
			"days",
			"min",
			"max",
			"round",
			"abs",
			"pow",
		}

		declared_vars = {m.variable_name for m in (self.factor_mappings or []) if m.variable_name}
		all_known = standard_vars.union(declared_vars)

		missing = formula_vars - all_known
		if missing:
			frappe.msgprint(
				_(
					"Note: Formula references variables not explicitly defined in factor mappings: {0}. "
					"Ensure these are provided in the order payload or built-ins."
				).format(", ".join(sorted(missing))),
				alert=True,
			)
