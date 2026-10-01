"""Dynamic Order Engine (Client Ordering & Policy Issuance Subsystem).

Coordinates:
1. Schema-driven form validation with dynamic `show_if` rules.
2. Server-side actuarial premium recalculation via Calculation Engine (`engine.py`).
3. Atomic partner limit deduction via Financial Engine (`partner_limits.py`).
4. Automated installment schedule generation.
5. Client profile resolution and Policy document issuance.
6. Integration with Uzbekistan national data validators (PINFL/INN/Phone).
"""

import json
import re
from datetime import date, datetime, timedelta
from typing import Any

from insurance_core.uz_validators import (
	normalize_uz_phone,
	validate_inn,
	validate_pinfl,
	validate_uz_phone,
)

try:
	import frappe
	from frappe import _
	from frappe.utils import add_days, flt, getdate, now_datetime, nowdate
except ImportError:
	# Mock environment for unit tests outside Frappe bench
	class _FrappeMock:
		session = type("Session", (), {"user": "Administrator"})()

		@staticmethod
		def whitelist(*args, **kwargs):
			return lambda fn: fn

		@staticmethod
		def throw(msg, *args, **kwargs):
			raise ValueError(msg)

		@staticmethod
		def log_error(*args, **kwargs):
			pass

		class db:
			@staticmethod
			def exists(doctype, name):
				return True

			@staticmethod
			def get_value(doctype, filters, fieldname):
				return None

	frappe = _FrappeMock()
	_ = lambda s: s  # noqa: E731
	flt = lambda v, default=0.0: float(v) if v is not None and v != "" else default  # noqa: E731
	nowdate = lambda: date.today().isoformat()  # noqa: E731
	now_datetime = datetime.now

	def getdate(v=None):
		if not v:
			return date.today()
		if isinstance(v, (date, datetime)):
			return v if isinstance(v, date) else v.date()
		return date.fromisoformat(str(v))

	def add_days(d, days):
		return getdate(d) + timedelta(days=days)


def evaluate_show_if(condition: str | None, data: dict[str, Any]) -> bool:
	"""Safely evaluate dynamic visibility expression against user input.

	Example condition: "vehicle_type == 'Truck'" or "driver_age < 21"
	"""
	if not condition or not str(condition).strip():
		return True

	cleaned = str(condition).strip()

	# Support simple JS/Python equality and comparison expressions
	# Pattern: variable (==|!=|>|<|>=|<=) value
	match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*(==|!=|>=|<=|>|<)\s*(.+)$", cleaned)
	if match:
		var_name, op, raw_val = match.groups()
		actual = data.get(var_name)

		target_val = raw_val.strip().strip("'\"")
		try:
			target_num = float(target_val)
			actual_num = float(actual) if actual is not None else 0.0
			if op == "==":
				return actual_num == target_num
			if op == "!=":
				return actual_num != target_num
			if op == ">":
				return actual_num > target_num
			if op == "<":
				return actual_num < target_num
			if op == ">=":
				return actual_num >= target_num
			if op == "<=":
				return actual_num <= target_num
		except (ValueError, TypeError):
			actual_str = str(actual or "").strip()
			if op == "==":
				return actual_str.lower() == target_val.lower()
			if op == "!=":
				return actual_str.lower() != target_val.lower()

	# Fallback safe boolean evaluation
	try:
		return bool(eval(cleaned, {"__builtins__": {}}, dict(data)))
	except Exception:
		return True


def validate_order_data(schema: list[dict[str, Any]], data: dict[str, Any]) -> list[str]:
	"""Validate submitted order form data against the JSON schema of the product.

	Returns a list of error messages (empty if valid).
	"""
	errors: list[str] = []

	for step in schema:
		fields = step.get("fields", [])
		for field in fields:
			fieldname = field.get("fieldname") or field.get("name")
			if not fieldname:
				continue

			label = field.get("label", fieldname)
			val = data.get(fieldname)

			# 1. Check dynamic visibility condition
			show_if = field.get("show_if") or field.get("condition")
			if show_if and not evaluate_show_if(show_if, data):
				continue  # Hidden field: skip validation

			# 2. Check required constraint
			is_reqd = bool(field.get("required") or field.get("reqd"))
			if is_reqd and (val is None or str(val).strip() == ""):
				errors.append(_("Поле '{0}' обязательно для заполнения").format(label))
				continue

			if val is None or str(val).strip() == "":
				continue

			# 3. Check regex format constraint
			regex_pat = field.get("regex") or field.get("validation_regex")
			if regex_pat:
				if not re.match(regex_pat, str(val).strip()):
					errors.append(
						_("Поле '{0}' не соответствует требуемому формату").format(label)
					)

			# 4. Check Uzbekistan-specific validators
			field_type_lower = str(field.get("type") or field.get("fieldtype", "")).lower()
			name_lower = fieldname.lower()

			if "pinfl" in name_lower or "jshshir" in name_lower:
				pinfl_res = validate_pinfl(str(val))
				if not pinfl_res["is_valid"]:
					errors.append(f"{label}: {pinfl_res['error']}")

			elif "inn" in name_lower or "stir" in name_lower:
				inn_res = validate_inn(str(val))
				if not inn_res["is_valid"]:
					errors.append(f"{label}: {inn_res['error']}")

			elif field_type_lower == "phone" or "phone" in name_lower or "mobile" in name_lower:
				if not validate_uz_phone(str(val)):
					errors.append(
						f"{label}: Укажите корректный номер телефона Узбекистана (+998XXXXXXXXX)"
					)

	return errors


@frappe.whitelist(allow_guest=True)
def get_order_schema(scheme: str) -> dict[str, Any]:
	"""Retrieve metadata and schema for the order wizard of a specific product."""
	if not frappe.db.exists("Insurance Scheme", scheme):
		frappe.throw(_("Insurance Scheme '{0}' not found").format(scheme))

	scheme_doc = frappe.get_doc("Insurance Scheme", scheme)

	raw_schema = getattr(scheme_doc, "order_form_schema", None)
	schema_list = []
	if raw_schema:
		try:
			schema_list = json.loads(raw_schema) if isinstance(raw_schema, str) else raw_schema
		except Exception:
			schema_list = []

	# Default fallback schema if none specified
	if not schema_list:
		schema_list = [
			{
				"step": 1,
				"step_title": _("Параметры страхования"),
				"fields": [
					{"fieldname": "sum_insured", "label": _("Страховая сумма (UZS)"), "type": "Number", "required": True},
					{"fieldname": "days", "label": _("Срок (дней)"), "type": "Number", "default": 365, "required": True},
				],
			},
			{
				"step": 2,
				"step_title": _("Данные страхователя"),
				"fields": [
					{"fieldname": "full_name", "label": _("ФИО страхователя"), "type": "Data", "required": True},
					{"fieldname": "pinfl", "label": _("ПИНФЛ"), "type": "Data", "regex": r"^\d{14}$", "required": True},
					{"fieldname": "phone", "label": _("Телефон"), "type": "Phone", "default": "+998", "required": True},
					{"fieldname": "email", "label": _("Email"), "type": "Data", "required": False},
				],
			},
		]

	widget_config = {}
	if getattr(scheme_doc, "widget_config", None):
		try:
			widget_config = json.loads(scheme_doc.widget_config)
		except Exception:
			widget_config = {}

	return {
		"scheme": scheme_doc.name,
		"scheme_id": getattr(scheme_doc, "scheme_id", scheme_doc.name),
		"scheme_name": getattr(scheme_doc, "scheme_name", scheme_doc.name),
		"line_of_business": getattr(scheme_doc, "line_of_business", "General"),
		"provider": getattr(scheme_doc, "provider", "AlfaInvest"),
		"description": getattr(scheme_doc, "description", ""),
		"order_form_schema": schema_list,
		"widget_config": widget_config,
		"terms_and_conditions": getattr(scheme_doc, "terms_and_conditions", ""),
		"available_payment_plans": [
			"100% Full Payment",
			"50/50 Split",
			"Quarterly (4x25%)",
			"Monthly (12x)",
			"Partner Credit Account",
		],
	}


@frappe.whitelist(allow_guest=True)
def calculate_order_premium(scheme: str, form_data: str | dict[str, Any] | None = None) -> dict[str, Any]:
	"""Live premium calculation endpoint for interactive wizards."""
	from insurance_core.engine import calculate_premium

	if isinstance(form_data, str):
		try:
			payload = json.loads(form_data)
		except Exception:
			payload = {}
	else:
		payload = dict(form_data or {})

	return calculate_premium(scheme, payload=payload, log_result=False)


@frappe.whitelist(allow_guest=True)
def submit_order(
	scheme: str,
	form_data: str | dict[str, Any],
	payment_method: str = "100% Full Payment",
	partner: str | None = None,
	partner_account: str | None = None,
	start_date: str | None = None,
) -> dict[str, Any]:
	"""Submit an order, validate constraints, deduct partner balance, and issue Policy."""
	from insurance_core.engine import calculate_premium
	from insurance_core.partner_limits import deduct_partner_limit, generate_installment_schedule

	if isinstance(form_data, str):
		try:
			data = json.loads(form_data)
		except Exception as e:
			frappe.throw(_("Invalid form_data JSON: {0}").format(e))
	else:
		data = dict(form_data or {})

	if not frappe.db.exists("Insurance Scheme", scheme):
		frappe.throw(_("Insurance Scheme '{0}' not found").format(scheme))

	scheme_doc = frappe.get_doc("Insurance Scheme", scheme)

	# 1. Validate against product schema
	raw_schema = getattr(scheme_doc, "order_form_schema", None)
	if raw_schema:
		try:
			schema_list = json.loads(raw_schema) if isinstance(raw_schema, str) else raw_schema
			validation_errors = validate_order_data(schema_list, data)
			if validation_errors:
				frappe.throw("<br>".join(validation_errors))
		except (ValueError, TypeError) as e:
			frappe.throw(str(e))

	# 2. Server-side authoritative premium recalculation
	calc_result = calculate_premium(scheme, payload=data, log_result=True)
	final_premium = flt(calc_result.get("final_premium", 0.0))
	sum_insured = flt(data.get("sum_insured") or getattr(scheme_doc, "minimum_sum_assured", 0.0))

	# 3. Resolve or create Insurance Client
	client_name = data.get("client")
	pinfl = data.get("pinfl")
	phone = normalize_uz_phone(data.get("phone"))
	email = data.get("email")
	full_name = data.get("full_name") or data.get("client_name") or "Покупатель полиса"

	if not client_name and pinfl:
		client_name = frappe.db.get_value("Insurance Client", {"tax_id": pinfl}, "name")
	if not client_name and email:
		client_name = frappe.db.get_value("Insurance Client", {"email": email}, "name")

	if not client_name:
		client_doc = frappe.get_doc({
			"doctype": "Insurance Client",
			"full_name": full_name,
			"phone": phone,
			"email": email,
			"tax_id": pinfl,
			"client_type": "Individual",
			"lifecycle_stage": "Active Policyholder",
		})
		client_doc.insert(ignore_permissions=True)
		client_name = client_doc.name

	# 4. Generate policy dates
	effective_start = getdate(start_date or data.get("start_date") or nowdate())
	term_days = int(data.get("days", 365))
	effective_end = add_days(effective_start, term_days - 1)

	# 5. Handle Partner Limit deduction (if paid via partner credit)
	limit_deducted = 0
	if payment_method == "Partner Credit Account" or partner_account or partner:
		target_account = partner_account
		if not target_account and partner:
			target_account = frappe.db.get_value(
				"Partner Credit Account", {"partner": partner, "status": "Active"}, "name"
			)
		if target_account:
			deduct_partner_limit(
				account_name=target_account,
				amount=final_premium,
				policy=None,
				reference=f"Order issue for {full_name} ({scheme})",
			)
			limit_deducted = 1

	# 6. Generate Installment Schedule
	installments = generate_installment_schedule(
		total_premium=final_premium,
		plan_type=payment_method,
		start_date=effective_start,
	)

	# 7. Create Insurance Policy record
	policy_doc = frappe.get_doc({
		"doctype": "Insurance Policy",
		"client": client_name,
		"scheme": scheme,
		"provider": scheme_doc.provider,
		"status": "Active" if limit_deducted or payment_method == "100% Full Payment" else "Submitted",
		"start_date": effective_start,
		"end_date": effective_end,
		"sum_assured": sum_insured,
		"total_premium": final_premium,
		"payment_status": "Paid" if limit_deducted else "Unpaid",
		"payment_plan": payment_method,
		"partner_account": partner_account,
		"limit_deducted": limit_deducted,
	})

	# Append installments
	for inst in installments:
		policy_doc.append("installments", {
			"installment_number": inst["installment_number"],
			"due_date": inst["due_date"],
			"amount": inst["amount"],
			"status": "Paid" if limit_deducted and inst["installment_number"] == 1 else "Unpaid",
		})

	policy_doc.insert(ignore_permissions=True)

	# 8. Regulatory EOIS Registration & QR generation
	from insurance_core.eis_gateway import register_policy_in_eis
	from insurance_core.notifications import send_policy_issued_notification
	from insurance_core.erp_sync import sync_policy_to_erp

	policy_number = getattr(policy_doc, "policy_number", policy_doc.name)
	eis_res = register_policy_in_eis(policy_doc)

	# 9. Send National SMS Notification
	if phone:
		send_policy_issued_notification(
			phone=phone,
			policy_number=policy_number,
			verification_url=eis_res.get("verification_url", ""),
			amount=final_premium,
		)

	# 10. ERP Accounting Sync
	sync_policy_to_erp(policy_doc.name)

	return {
		"success": True,
		"policy_name": policy_doc.name,
		"policy_number": policy_number,
		"scheme": scheme,
		"client": client_name,
		"total_premium": final_premium,
		"status": policy_doc.status,
		"installments": installments,
		"eois_number": eis_res.get("eois_registration_number"),
		"verification_url": eis_res.get("verification_url"),
		"qr_svg": eis_res.get("qr_svg"),
		"breakdown": calc_result.get("breakdown", []),
	}
