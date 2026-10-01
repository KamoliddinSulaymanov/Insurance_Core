"""Insurance Product Factory Management Module.

Implements:
1. Product Locking (Concurrency control / anti-collision editing - ТЗ 4.8.2.8)
2. Product Lifecycle: Review -> Signing -> Publishing (ТЗ 4.8.2.1, 4.8.2.2)
3. Full JSON Bundle Export & Import (ТЗ 4.8.2.6, 4.8.2.7)
"""

import json
from datetime import datetime, timedelta
from typing import Any

try:
	import frappe
	from frappe import _
	from frappe.utils import get_datetime, now_datetime
except ImportError:
	class _FrappeMock:
		@staticmethod
		def whitelist(*args, **kwargs):
			return lambda fn: fn

		@staticmethod
		def throw(msg, *args, **kwargs):
			raise ValueError(msg)

		@staticmethod
		def log_error(*args, **kwargs):
			pass

	frappe = _FrappeMock()
	_ = lambda s: s  # noqa: E731
	now_datetime = datetime.now

	def get_datetime(v):
		if isinstance(v, datetime):
			return v
		if isinstance(v, str):
			return datetime.fromisoformat(v)
		return datetime.now()


LOCK_TIMEOUT_MINUTES = 15


# ---------------------------------------------------------------------------
# 1. Product Locking & Concurrency Protection
# ---------------------------------------------------------------------------

@frappe.whitelist()
def lock_product(scheme_name: str, user: str | None = None) -> dict[str, Any]:
	"""Lock a product for editing.

	If already locked by another user and not expired, refuses lock.
	"""
	if not scheme_name or not frappe.db.exists("Insurance Scheme", scheme_name):
		frappe.throw(_("Insurance Scheme '{0}' not found").format(scheme_name))

	doc = frappe.get_doc("Insurance Scheme", scheme_name)
	current_user = user or (frappe.session.user if hasattr(frappe, "session") else "Administrator")
	now = now_datetime()

	# Check existing lock
	if doc.get("is_locked") and doc.get("locked_by") and doc.get("locked_by") != current_user:
		locked_at = get_datetime(doc.locked_at) if doc.get("locked_at") else None
		if locked_at and (now - locked_at) < timedelta(minutes=LOCK_TIMEOUT_MINUTES):
			return {
				"success": False,
				"is_locked": True,
				"locked_by": doc.locked_by,
				"locked_at": str(doc.locked_at),
				"message": _("Product is currently locked by user {0} since {1}").format(
					doc.locked_by, doc.locked_at
				),
			}

	# Acquire or refresh lock
	doc.is_locked = 1
	doc.locked_by = current_user
	doc.locked_at = now
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	return {
		"success": True,
		"is_locked": True,
		"locked_by": current_user,
		"locked_at": str(now),
		"message": _("Product locked successfully for editing"),
	}


@frappe.whitelist()
def unlock_product(scheme_name: str, user: str | None = None, force: int = 0) -> dict[str, Any]:
	"""Release the editing lock on a product."""
	if not scheme_name or not frappe.db.exists("Insurance Scheme", scheme_name):
		frappe.throw(_("Insurance Scheme '{0}' not found").format(scheme_name))

	doc = frappe.get_doc("Insurance Scheme", scheme_name)
	current_user = user or (frappe.session.user if hasattr(frappe, "session") else "Administrator")

	if doc.get("is_locked"):
		# Allow owner of lock, System Manager, or force=1 to unlock
		if doc.locked_by != current_user and not force:
			is_mgr = "System Manager" in frappe.get_roles(current_user) if hasattr(frappe, "get_roles") else False
			if not is_mgr:
				frappe.throw(_("Cannot unlock: Product is locked by {0}").format(doc.locked_by))

		doc.is_locked = 0
		doc.locked_by = None
		doc.locked_at = None
		doc.save(ignore_permissions=True)
		frappe.db.commit()

	return {"success": True, "is_locked": False, "message": _("Product unlocked")}


# ---------------------------------------------------------------------------
# 2. Product Lifecycle & Signing
# ---------------------------------------------------------------------------

@frappe.whitelist()
def submit_for_review(scheme_name: str) -> dict[str, Any]:
	"""Submit product to 'Under Review' status."""
	doc = frappe.get_doc("Insurance Scheme", scheme_name)
	doc.status = "Under Review"
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"success": True, "status": doc.status}


@frappe.whitelist()
def sign_product(scheme_name: str, user: str | None = None) -> dict[str, Any]:
	"""Underwriter signs the product before publication.

	Validates:
	- Calculation rule syntax (if linked)
	- Order form schema (if provided)
	"""
	doc = frappe.get_doc("Insurance Scheme", scheme_name)
	current_user = user or (frappe.session.user if hasattr(frappe, "session") else "Administrator")

	# Validate order_form_schema JSON if present
	if doc.get("order_form_schema"):
		try:
			json.loads(doc.order_form_schema)
		except Exception as e:
			frappe.throw(_("Invalid Order Form Schema JSON: {0}").format(e))

	# Validate widget_config JSON if present
	if doc.get("widget_config"):
		try:
			json.loads(doc.widget_config)
		except Exception as e:
			frappe.throw(_("Invalid Widget Config JSON: {0}").format(e))

	# Validate calculation rule if linked
	rule_name = doc.get("calculation_rule") or frappe.db.get_value(
		"Product Calculation Rule", {"scheme": scheme_name, "is_active": 1}, "name"
	)
	if rule_name:
		rule = frappe.get_doc("Product Calculation Rule", rule_name)
		rule.validate_formula()

	doc.signed_by = current_user
	doc.signed_at = now_datetime()
	doc.status = "Signed"
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	return {
		"success": True,
		"status": doc.status,
		"signed_by": current_user,
		"signed_at": str(doc.signed_at),
		"message": _("Product '{0}' signed successfully").format(doc.scheme_name),
	}


@frappe.whitelist()
def publish_product(scheme_name: str) -> dict[str, Any]:
	"""Publish product to B2B Partner Portal and Widget."""
	doc = frappe.get_doc("Insurance Scheme", scheme_name)

	# Must be signed before publishing
	if doc.status not in ("Signed", "Draft"):
		is_admin = hasattr(frappe, "session") and "System Manager" in frappe.get_roles(frappe.session.user)
		if not is_admin:
			frappe.throw(
				_("Product must be in 'Signed' status before publication (current status: {0})").format(
					doc.status
				)
			)

	doc.status = "Published"
	doc.is_locked = 0
	doc.locked_by = None
	doc.locked_at = None
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	return {
		"success": True,
		"status": doc.status,
		"message": _("Product '{0}' is now Published and live for orders").format(doc.scheme_name),
	}


# ---------------------------------------------------------------------------
# 3. Product Bundle Export & Import (JSON)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def export_product_bundle(scheme_name: str) -> dict[str, Any]:
	"""Export complete product configuration and all dependencies to JSON."""
	if not frappe.db.exists("Insurance Scheme", scheme_name):
		frappe.throw(_("Insurance Scheme '{0}' not found").format(scheme_name))

	scheme = frappe.get_doc("Insurance Scheme", scheme_name)
	scheme_dict = scheme.as_dict()

	# Remove site-specific volatile fields
	for k in ("modified", "creation", "owner", "modified_by", "_comment_count", "_liked_by"):
		scheme_dict.pop(k, None)

	# Collect linked Calculation Rule
	rule_name = scheme.get("calculation_rule") or frappe.db.get_value(
		"Product Calculation Rule", {"scheme": scheme_name, "is_active": 1}, "name"
	)

	rule_data = None
	matrices_data: list[dict[str, Any]] = []
	factors_data: list[dict[str, Any]] = []

	if rule_name:
		rule = frappe.get_doc("Product Calculation Rule", rule_name)
		rule_data = rule.as_dict()
		for k in ("modified", "creation", "owner", "modified_by"):
			rule_data.pop(k, None)

		# Collect referenced matrices and factors
		matrix_names = {
			m.tariff_matrix for m in (rule.factor_mappings or []) if m.source_type == "Tariff Matrix" and m.tariff_matrix
		}
		factor_names = {
			m.tariff_factor for m in (rule.factor_mappings or []) if m.source_type == "Input Factor" and m.tariff_factor
		}

		for m_name in matrix_names:
			if frappe.db.exists("Tariff Matrix", m_name):
				m_doc = frappe.get_doc("Tariff Matrix", m_name)
				m_dict = m_doc.as_dict()
				for k in ("modified", "creation", "owner", "modified_by"):
					m_dict.pop(k, None)
				matrices_data.append(m_dict)
				# Also collect factors linked in matrix dimensions
				for dim_fld in ("dim1_factor", "dim2_factor", "dim3_factor"):
					f_val = m_doc.get(dim_fld)
					if f_val:
						factor_names.add(f_val)

		for f_name in factor_names:
			if frappe.db.exists("Tariff Factor", f_name):
				f_doc = frappe.get_doc("Tariff Factor", f_name)
				f_dict = f_doc.as_dict()
				for k in ("modified", "creation", "owner", "modified_by"):
					f_dict.pop(k, None)
				factors_data.append(f_dict)

	bundle = {
		"bundle_version": "1.0",
		"bundle_type": "AlfaInvest_Product_Package",
		"exported_at": str(now_datetime()),
		"product": scheme_dict,
		"calculation_rule": rule_data,
		"tariff_matrices": matrices_data,
		"tariff_factors": factors_data,
	}

	return bundle


@frappe.whitelist()
def import_product_bundle(bundle_payload: str | dict[str, Any], overwrite: int = 1) -> dict[str, Any]:
	"""Import a product bundle JSON and recreate/update all components."""
	if isinstance(bundle_payload, str):
		try:
			bundle = json.loads(bundle_payload)
		except Exception as e:
			frappe.throw(_("Invalid JSON payload: {0}").format(e))
	else:
		bundle = dict(bundle_payload)

	product_data = bundle.get("product")
	if not product_data or not product_data.get("scheme_id"):
		frappe.throw(_("Bundle does not contain valid product metadata"))

	scheme_id = product_data["scheme_id"]

	# 1. Restore Tariff Factors
	imported_factors = 0
	for f_dict in bundle.get("tariff_factors") or []:
		code = f_dict.get("factor_code")
		if not code:
			continue
		if frappe.db.exists("Tariff Factor", code):
			if overwrite:
				doc = frappe.get_doc("Tariff Factor", code)
				doc.update(f_dict)
				doc.save(ignore_permissions=True)
		else:
			frappe.get_doc({"doctype": "Tariff Factor", **f_dict}).insert(ignore_permissions=True)
		imported_factors += 1

	# 2. Restore Tariff Matrices
	imported_matrices = 0
	for m_dict in bundle.get("tariff_matrices") or []:
		code = m_dict.get("matrix_code")
		if not code:
			continue
		if frappe.db.exists("Tariff Matrix", code):
			if overwrite:
				doc = frappe.get_doc("Tariff Matrix", code)
				doc.update(m_dict)
				doc.save(ignore_permissions=True)
		else:
			frappe.get_doc({"doctype": "Tariff Matrix", **m_dict}).insert(ignore_permissions=True)
		imported_matrices += 1

	# 3. Restore Product Calculation Rule
	rule_data = bundle.get("calculation_rule")
	if rule_data and rule_data.get("rule_name"):
		rule_name = rule_data["rule_name"]
		if frappe.db.exists("Product Calculation Rule", rule_name):
			if overwrite:
				doc = frappe.get_doc("Product Calculation Rule", rule_name)
				doc.update(rule_data)
				doc.save(ignore_permissions=True)
		else:
			frappe.get_doc({"doctype": "Product Calculation Rule", **rule_data}).insert(ignore_permissions=True)

	# 4. Restore or Update Insurance Scheme
	if frappe.db.exists("Insurance Scheme", scheme_id):
		if overwrite:
			scheme = frappe.get_doc("Insurance Scheme", scheme_id)
			scheme.update(product_data)
			scheme.save(ignore_permissions=True)
	else:
		scheme = frappe.get_doc({"doctype": "Insurance Scheme", **product_data})
		scheme.insert(ignore_permissions=True)

	frappe.db.commit()

	return {
		"success": True,
		"scheme_id": scheme_id,
		"factors_imported": imported_factors,
		"matrices_imported": imported_matrices,
		"rule_imported": bool(rule_data),
		"message": _("Product '{0}' and dependencies imported successfully").format(scheme_id),
	}
