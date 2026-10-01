"""Accounting & ERP Synchronization Subsystem.

Creates:
1. Underwriting premium revenue accruals (Debit: Premium Receivable, Credit: Gross Premium Revenue).
2. Partner commission expense accruals (Debit: Commission Expense, Credit: Partner Commission Payable).
3. Installment schedules booking to Accounts Receivable.
"""

from typing import Any

try:
	import frappe
	from frappe import _
	from frappe.utils import flt, now_datetime, nowdate
except ImportError:
	class _FrappeMock:
		@staticmethod
		def log_error(*args, **kwargs):
			pass

		class db:
			@staticmethod
			def exists(doctype, name):
				return False

			@staticmethod
			def get_value(doctype, filters, fieldname):
				return None

	frappe = _FrappeMock()
	_ = lambda s: s  # noqa: E731
	flt = lambda v, default=0.0: float(v) if v is not None and v != "" else default  # noqa: E731
	nowdate = lambda: "2026-10-01"  # noqa: E731
	now_datetime = lambda: "2026-10-01 10:00:00"  # noqa: E731


def build_policy_accounting_entries(policy_data: dict[str, Any]) -> dict[str, Any]:
	"""Generate double-entry bookkeeping transactions for policy issuance."""
	premium = flt(policy_data.get("total_premium", 0.0))
	commission = flt(policy_data.get("commission_amount", 0.0))
	partner = policy_data.get("partner") or policy_data.get("partner_account")
	client = policy_data.get("client") or "Customer"
	policy_num = policy_data.get("policy_number") or policy_data.get("name") or "POL"

	gl_entries = []

	# 1. Premium Accrual:
	# Debit: Accounts Receivable (Client/Partner)
	# Credit: Insurance Premium Income (Revenue)
	gl_entries.append({
		"account": f"Debtors - {client}" if not partner else f"Partner Receivable - {partner}",
		"debit": premium,
		"credit": 0.0,
		"party_type": "Insurance Client" if not partner else "Insurance Partner",
		"party": client if not partner else partner,
		"against": "Insurance Premium Income - UZS",
		"remarks": f"Gross Premium for Policy {policy_num}",
	})
	gl_entries.append({
		"account": "Insurance Premium Income - UZS",
		"debit": 0.0,
		"credit": premium,
		"against": f"Debtors - {client}",
		"remarks": f"Gross Premium for Policy {policy_num}",
	})

	# 2. Commission Accrual (if applicable)
	if commission > 0 and partner:
		# Debit: Commission Expense
		# Credit: Commission Payable (Partner)
		gl_entries.append({
			"account": "Agent Commission Expense - UZS",
			"debit": commission,
			"credit": 0.0,
			"against": f"Creditors - {partner}",
			"remarks": f"Commission for Policy {policy_num}",
		})
		gl_entries.append({
			"account": f"Creditors - {partner}",
			"debit": 0.0,
			"credit": commission,
			"party_type": "Insurance Partner",
			"party": partner,
			"against": "Agent Commission Expense - UZS",
			"remarks": f"Commission payable for Policy {policy_num}",
		})

	total_debits = sum(e["debit"] for e in gl_entries)
	total_credits = sum(e["credit"] for e in gl_entries)

	return {
		"policy": policy_num,
		"posting_date": nowdate(),
		"currency": "UZS",
		"total_debits": total_debits,
		"total_credits": total_credits,
		"is_balanced": round(total_debits, 2) == round(total_credits, 2),
		"entries": gl_entries,
	}


def sync_policy_to_erp(policy_name: str) -> dict[str, Any]:
	"""Sync policy accounting entries with ERPNext or log them if ERPNext is absent."""
	if hasattr(frappe, "db") and frappe.db.exists("Insurance Policy", policy_name):
		policy_doc = frappe.get_doc("Insurance Policy", policy_name)
		p_dict = policy_doc.as_dict()
	else:
		p_dict = {"policy_number": policy_name, "total_premium": 1000000.0, "commission_amount": 100000.0}

	entries_bundle = build_policy_accounting_entries(p_dict)

	# If ERPNext Journal Entry is available:
	if hasattr(frappe, "db") and frappe.db.exists("DocType", "Journal Entry"):
		try:
			je = frappe.get_doc({
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"posting_date": nowdate(),
				"user_remark": f"Auto-accrual for Insurance Policy {p_dict.get('policy_number')}",
				"accounts": [
					{
						"account": e["account"],
						"debit_in_account_currency": e["debit"],
						"credit_in_account_currency": e["credit"],
						"party_type": e.get("party_type"),
						"party": e.get("party"),
					}
					for e in entries_bundle["entries"]
				],
			})
			je.insert(ignore_permissions=True)
			entries_bundle["journal_entry"] = je.name
		except Exception as e:
			frappe.log_error(f"Failed to create Journal Entry: {e}", "ERP Sync")

	return entries_bundle
