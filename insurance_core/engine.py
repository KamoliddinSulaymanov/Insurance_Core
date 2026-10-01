"""Universal No-Code Calculation Engine for Insurance Core.

Provides dynamic, safe actuarial premium evaluation driven by:
- Tariff Factors (inputs / variables)
- Tariff Matrices (N-dimensional coefficient lookup tables)
- Product Calculation Rules (formula + AST safe_eval + surcharges)
"""

import ast
import json
import math
from typing import Any

try:
	import frappe
	from frappe import _
	from frappe.utils import flt, now_datetime
	from frappe.utils.safe_exec import safe_eval
except ImportError:
	# Standalone fallback for testing/execution outside of Frappe bench environment
	class _FrappeMock:
		@staticmethod
		def whitelist(*args, **kwargs):
			return lambda fn: fn

		@staticmethod
		def log_error(*args, **kwargs):
			pass

		@staticmethod
		def throw(msg, *args, **kwargs):
			raise ValueError(msg)

	frappe = _FrappeMock()
	_ = lambda s: s  # noqa: E731
	flt = lambda v, default=0.0: float(v) if v is not None and v != "" else default  # noqa: E731
	from datetime import datetime
	now_datetime = datetime.now
	def safe_eval(expr, eval_globals=None, eval_locals=None):
		g = {"__builtins__": {}}
		if eval_globals:
			g.update(eval_globals)
		l = dict(eval_locals or {})
		return eval(expr, g, l)

# Standard safe math functions exposed to calculation formulas
SAFE_MATH = {
	"min": min,
	"max": max,
	"round": round,
	"abs": abs,
	"pow": pow,
	"ceil": math.ceil,
	"floor": math.floor,
}


def _try_float(val: Any) -> float | None:
	"""Convert to float if numeric, else return None."""
	if val is None or val == "":
		return None
	try:
		return float(val)
	except (ValueError, TypeError):
		return None


def match_dimension(val: Any, bound_from: Any, bound_to: Any) -> bool:
	"""Match an input value against a dimension range or exact value."""
	if bound_from is None and bound_to is None:
		return True

	from_num = _try_float(bound_from)
	to_num = _try_float(bound_to)
	val_num = _try_float(val)

	# If numbers: range check
	if val_num is not None:
		if from_num is not None and val_num < from_num:
			return False
		if to_num is not None and val_num > to_num:
			return False
		# If both from_num and to_num were None, but bound_from was a string
		if from_num is None and bound_from:
			return str(val).strip().lower() == str(bound_from).strip().lower()
		return True

	# If strings: exact match or comma-separated list
	val_str = str(val or "").strip().lower()
	if bound_from:
		targets = [t.strip().lower() for t in str(bound_from).split(",") if t.strip()]
		return val_str in targets

	return True


def lookup_matrix(matrix_doc_or_name: Any, input_data: dict[str, Any]) -> tuple[float, float, str]:
	"""Lookup coefficient and amount from a Tariff Matrix given input data.

	Returns (rate, fixed_amount, explanation_note).
	"""
	if not matrix_doc_or_name:
		return 1.0, 0.0, "No matrix specified"

	if isinstance(matrix_doc_or_name, str):
		matrix = frappe.get_doc("Tariff Matrix", matrix_doc_or_name)
	else:
		matrix = matrix_doc_or_name

	dim1_val = input_data.get(matrix.dim1_factor) if matrix.dim1_factor else None
	dim2_val = input_data.get(matrix.dim2_factor) if matrix.dim2_factor else None
	dim3_val = input_data.get(matrix.dim3_factor) if matrix.dim3_factor else None

	for row in matrix.rows or []:
		# Check dimension 1
		if not match_dimension(dim1_val, row.dim1_from, row.dim1_to):
			continue

		# Check dimension 2 if defined
		if matrix.dim2_factor:
			if not match_dimension(dim2_val, row.dim2_from, row.dim2_to):
				continue

		# Check dimension 3 if defined
		if matrix.dim3_factor:
			if not match_dimension(dim3_val, row.dim3_val, None):
				continue

		rate = flt(row.rate) if getattr(row, "rate", None) not in (None, "") else 1.0
		amount = flt(row.amount) if getattr(row, "amount", None) not in (None, "") else 0.0
		note = (
			f"Matched matrix '{matrix.matrix_name}': rate={rate}, amount={amount}"
		)
		return rate, amount, note

	default_rate = flt(matrix.default_rate) if getattr(matrix, "default_rate", None) not in (None, "") else 1.0
	return default_rate, 0.0, f"Matrix '{matrix.matrix_name}' fallback rate={default_rate}"


def resolve_factor_value(mapping: Any, input_data: dict[str, Any], context: dict[str, Any]) -> tuple[float, str]:
	"""Resolve the numeric value of a mapped formula variable."""
	source_type = mapping.source_type
	fallback = flt(mapping.fallback_value) if getattr(mapping, "fallback_value", None) not in (None, "") else 1.0

	if source_type == "Constant":
		val = flt(mapping.constant_value) if getattr(mapping, "constant_value", None) not in (None, "") else fallback
		return val, f"Constant {mapping.variable_name} = {val}"

	if source_type == "Input Factor":
		factor_code = mapping.tariff_factor
		if not factor_code:
			return fallback, f"Missing factor link for {mapping.variable_name}, using fallback {fallback}"

		raw_val = input_data.get(factor_code)
		num_val = _try_float(raw_val)
		if num_val is not None:
			return num_val, f"Factor {factor_code} = {num_val}"
		elif raw_val is not None:
			# Boolean or string
			if isinstance(raw_val, bool) or str(raw_val).lower() in ("true", "1", "yes"):
				return 1.0, f"Factor {factor_code} = 1.0 (True)"
			elif str(raw_val).lower() in ("false", "0", "no"):
				return 0.0, f"Factor {factor_code} = 0.0 (False)"
		return fallback, f"Factor {factor_code} not provided/invalid, using fallback {fallback}"

	if source_type == "Tariff Matrix":
		matrix_code = mapping.tariff_matrix
		if not matrix_code:
			return fallback, f"Missing matrix link for {mapping.variable_name}, using fallback {fallback}"

		rate, amount, note = lookup_matrix(matrix_code, input_data)
		# Variable value takes the rate by default
		return rate, f"{mapping.variable_name} from {note}"

	return fallback, f"{mapping.variable_name} default fallback {fallback}"


def evaluate_surcharges(
	surcharges: list[Any],
	current_premium: float,
	eval_context: dict[str, Any],
) -> tuple[float, list[str]]:
	"""Apply conditional surcharges, discounts and rules."""
	breakdown = []
	result_premium = current_premium

	for rule in surcharges or []:
		cond = (rule.condition or "").strip()
		if not cond:
			continue

		try:
			is_applicable = bool(safe_eval(cond, None, eval_context))
		except Exception as e:
			frappe.log_error(
				f"Error evaluating surcharge condition '{cond}': {e}",
				"Insurance Core Calculation Surcharge",
			)
			continue

		if not is_applicable:
			continue

		action = rule.action_type
		val = flt(rule.action_value)
		title = rule.title or rule.condition

		if action == "Multiply Rate":
			result_premium *= val
			breakdown.append(f"Surcharge '{title}': multiplied by {val} -> {result_premium:,.2f}")
		elif action == "Add Amount":
			result_premium += val
			breakdown.append(f"Surcharge '{title}': added {val:,.2f} -> {result_premium:,.2f}")
		elif action == "Subtract Amount":
			result_premium = max(0.0, result_premium - val)
			breakdown.append(f"Discount '{title}': subtracted {val:,.2f} -> {result_premium:,.2f}")
		elif action == "Discount Percent":
			discount = result_premium * (val / 100.0)
			result_premium = max(0.0, result_premium - discount)
			breakdown.append(f"Discount '{title}': {val}% (-{discount:,.2f}) -> {result_premium:,.2f}")

		# Update context premium for sequential dependent conditions
		eval_context["premium"] = result_premium

	return result_premium, breakdown


@frappe.whitelist()
def calculate_premium(
	scheme: str,
	payload: str | dict[str, Any] | None = None,
	log_result: bool = True,
	policy: str | None = None,
	quotation: str | None = None,
) -> dict[str, Any]:
	"""Universal premium calculation entrypoint.

	Supports:
	- Product Calculation Rule (Dynamic No-Code)
	- Graceful fallback to legacy insurance_core.premium.calculate_premium
	"""
	if isinstance(payload, str):
		try:
			input_data = json.loads(payload)
		except Exception:
			input_data = {}
	else:
		input_data = dict(payload or {})

	if not frappe.db.exists("Insurance Scheme", scheme):
		frappe.throw(_("Insurance Scheme '{0}' not found").format(scheme))

	# 1. Check if a dynamic Product Calculation Rule exists for this scheme
	rule_name = frappe.db.get_value(
		"Product Calculation Rule",
		{"scheme": scheme, "is_active": 1},
		"name",
	)

	# If no dynamic rule, fallback to legacy scheme_premium_slab logic
	if not rule_name:
		from insurance_core.premium import calculate_premium as legacy_calc

		age = input_data.get("age") or input_data.get("driver_age")
		sum_insured = input_data.get("sum_insured")
		members = input_data.get("members", 1)
		return legacy_calc(
			scheme,
			age=age,
			sum_insured=sum_insured,
			members=members,
			extras=input_data,
			log=log_result,
			policy=policy,
			quotation=quotation,
		)

	rule = frappe.get_doc("Product Calculation Rule", rule_name)
	breakdown: list[str] = []

	# 2. Build evaluation context
	base_premium = flt(rule.base_premium)
	sum_insured = flt(input_data.get("sum_insured", 0.0))
	members = flt(input_data.get("members", 1))
	days = flt(input_data.get("days", 365))

	context: dict[str, Any] = {
		**SAFE_MATH,
		**input_data,
		"base_premium": base_premium,
		"sum_insured": sum_insured,
		"members": members,
		"days": days,
	}

	breakdown.append(f"Base Premium = {base_premium:,.2f}")
	if sum_insured:
		breakdown.append(f"Sum Insured = {sum_insured:,.2f}")

	# 3. Resolve all variable mappings
	resolved_vars: dict[str, float] = {}
	for mapping in rule.factor_mappings or []:
		var_name = mapping.variable_name
		if not var_name:
			continue
		val, note = resolve_factor_value(mapping, input_data, context)
		context[var_name] = val
		resolved_vars[var_name] = val
		breakdown.append(note)

	# 4. Evaluate main formula
	formula = rule.formula or "base_premium"
	try:
		raw_premium = flt(safe_eval(formula, None, context))
		breakdown.append(f"Formula: [{formula}] -> Raw Premium = {raw_premium:,.2f}")
	except Exception as e:
		frappe.throw(
			_("Calculation formula failed for rule '{0}': {1}").format(rule.rule_name, e)
		)

	context["premium"] = raw_premium

	# 5. Apply conditional surcharges / discounts
	surcharged_premium, surcharge_notes = evaluate_surcharges(
		rule.surcharges, raw_premium, context
	)
	breakdown.extend(surcharge_notes)

	# 6. Apply floor / ceiling constraints
	final_premium = surcharged_premium
	min_prem = flt(rule.min_premium)
	max_prem = flt(rule.max_premium)

	if min_prem > 0 and final_premium < min_prem:
		breakdown.append(f"Clamped to Minimum Premium Floor: {min_prem:,.2f}")
		final_premium = min_prem
	elif max_prem > 0 and final_premium > max_prem:
		breakdown.append(f"Clamped to Maximum Premium Ceiling: {max_prem:,.2f}")
		final_premium = max_prem

	final_premium = round(final_premium, 2)
	net_premium = round(surcharged_premium, 2)

	# 7. Audit log in Premium Calculation Log
	if log_result and frappe.db.exists("DocType", "Premium Calculation Log"):
		try:
			log_doc = frappe.get_doc(
				{
					"doctype": "Premium Calculation Log",
					"scheme": scheme,
					"policy": policy,
					"quotation": quotation,
					"age": int(input_data.get("age") or input_data.get("driver_age") or 0),
					"sum_insured": sum_insured,
					"members": int(members),
					"net_premium": net_premium,
					"tax_amount": 0.0,
					"total_premium": final_premium,
					"breakdown": "\n".join(breakdown),
					"calculated_by": frappe.session.user if frappe.session else "Administrator",
					"calculated_at": now_datetime(),
				}
			)
			log_doc.insert(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(f"Failed to write Premium Calculation Log: {e}", "Insurance Engine")

	return {
		"scheme": scheme,
		"rule": rule.name,
		"final_premium": final_premium,
		"net_premium": net_premium,
		"base_premium": base_premium,
		"sum_insured": sum_insured,
		"resolved_factors": resolved_vars,
		"breakdown": breakdown,
	}
