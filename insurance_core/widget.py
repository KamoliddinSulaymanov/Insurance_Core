"""Embeddable Partner Widget Subsystem (JS SDK & Public B2B API).

Enables banks, car dealerships, and partner portals (e.g., avia.alfainvest.uz)
to embed real-time insurance calculation and order issuance on any external website.
"""

import json
from typing import Any

from insurance_core.order_engine import calculate_order_premium, submit_order

try:
	import frappe
	from frappe import _
except ImportError:
	class _FrappeMock:
		response = {}

		@staticmethod
		def whitelist(*args, **kwargs):
			return lambda fn: fn

		@staticmethod
		def throw(msg, *args, **kwargs):
			raise ValueError(msg)

		@staticmethod
		def get_doc(doctype, name=None):
			from types import SimpleNamespace
			return SimpleNamespace(
				name=name or doctype,
				scheme_id=name or doctype,
				scheme_name=name or doctype,
				line_of_business="General",
				provider="AlfaInvest",
				order_form_schema=None,
				widget_config=None,
			)

		class db:
			@staticmethod
			def exists(doctype, name):
				return True

			@staticmethod
			def get_value(doctype, filters, fieldname):
				return None

	frappe = _FrappeMock()
	_ = lambda s: s  # noqa: E731


def set_cors_headers():
	"""Enable Cross-Origin Resource Sharing for external website widgets."""
	try:
		if hasattr(frappe, "response"):
			frappe.response["headers"] = frappe.response.get("headers", {})
			frappe.response["headers"]["Access-Control-Allow-Origin"] = "*"
			frappe.response["headers"]["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
			frappe.response["headers"][
				"Access-Control-Allow-Headers"
			] = "Origin, X-Requested-With, Content-Type, Accept, Authorization"
	except Exception:
		pass


@frappe.whitelist(allow_guest=True)
def get_widget_bundle(scheme: str, partner: str | None = None) -> dict[str, Any]:
	"""Return configuration, schema, and theme data for embeddable partner widget."""
	set_cors_headers()

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

	raw_widget_cfg = getattr(scheme_doc, "widget_config", None)
	widget_cfg = {
		"title": getattr(scheme_doc, "scheme_name", scheme),
		"primary_color": "#D32F2F",
		"border_radius": "8px",
		"show_breakdown": True,
		"logo_url": "/assets/insurance_core/images/alfainvest_logo.svg",
	}
	if raw_widget_cfg:
		try:
			parsed_cfg = json.loads(raw_widget_cfg) if isinstance(raw_widget_cfg, str) else raw_widget_cfg
			widget_cfg.update(parsed_cfg)
		except Exception:
			pass

	partner_info = None
	if partner:
		partner_doc = frappe.db.get_value(
			"Partner Credit Account",
			{"partner": partner, "is_active": 1},
			["name", "partner", "account_type", "sanctioned_credit_limit"],
			as_dict=True,
		)
		if partner_doc:
			partner_info = {
				"partner": partner,
				"account": partner_doc.name,
				"account_type": partner_doc.account_type,
			}

	return {
		"scheme": scheme_doc.name,
		"scheme_id": getattr(scheme_doc, "scheme_id", scheme_doc.name),
		"scheme_name": getattr(scheme_doc, "scheme_name", scheme_doc.name),
		"line_of_business": getattr(scheme_doc, "line_of_business", "General"),
		"order_form_schema": schema_list,
		"widget_config": widget_cfg,
		"partner": partner_info,
	}


@frappe.whitelist(allow_guest=True)
def calculate_widget_premium(scheme: str, payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	"""CORS-enabled calculation endpoint for external widgets."""
	set_cors_headers()
	return calculate_order_premium(scheme, payload)


@frappe.whitelist(allow_guest=True)
def submit_widget_order(
	scheme: str,
	order_data: str | dict[str, Any],
	partner: str | None = None,
	partner_account: str | None = None,
) -> dict[str, Any]:
	"""CORS-enabled order submission endpoint for external partner widgets."""
	set_cors_headers()
	payment_method = "Partner Credit Account" if (partner or partner_account) else "100% Full Payment"
	return submit_order(
		scheme=scheme,
		form_data=order_data,
		payment_method=payment_method,
		partner=partner,
		partner_account=partner_account,
	)
