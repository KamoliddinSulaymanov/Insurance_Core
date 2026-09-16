# Copyright (c) 2026, Vivaswan Works and contributors
# License: MIT
"""
Installation / setup script for the Broker RFQ Extension.

Run after the DocType files and rfq.py are already in the app:

    bench --site <site> execute insurance_core.rfq_extension.install_rfq_extension.setup

Or from a console / after_migrate hook:

    from insurance_core.rfq_extension.install_rfq_extension import setup
    setup()

What this script does automatically
-----------------------------------
1. Creates required fields on *our* DocTypes only
   (Insurance Provider, Insurance Opportunity, Insurance Quotation)
2. Ensures Client Scripts for Opportunity + Insurance RFQ Detail
3. Seeds a couple of sample Insurer RFQ Rules (if none exist)
4. Prints a clear checklist for the remaining manual steps

What it does NOT do (by design)
-------------------------------
- Modify any ERPNext core DocType (RFQ, Supplier Quotation, Supplier, …)
- Copy source files into the app (developer must place them once)
- Patch hooks.py automatically (prints the exact snippet to add)
- Link every Insurance Provider → Supplier (data entry)
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


# ---------------------------------------------------------------------------
# Custom fields (only on our DocTypes)
# ---------------------------------------------------------------------------

CUSTOM_FIELDS = {
	"Insurance Provider": [
		{
			"fieldname": "erpnext_supplier",
			"label": "ERPNext Supplier",
			"fieldtype": "Link",
			"options": "Supplier",
			"insert_after": "provider_code",
			"in_standard_filter": 1,
			"description": "Maps this insurer to an ERPNext Supplier for RFQ suppliers table",
		},
	],
	"Insurance Opportunity": [
		{
			"fieldname": "line_of_business",
			"label": "Line of Business",
			"fieldtype": "Select",
			"options": "Health\nAuto\nLife\nProperty\nTravel\nMarine\nLiability",
			"insert_after": "insurance_scheme",
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
		{
			"fieldname": "required_sum_insured",
			"label": "Required Sum Insured",
			"fieldtype": "Currency",
			"insert_after": "expected_premium",
			"in_list_view": 1,
		},
		{
			"fieldname": "proposer_age",
			"label": "Proposer / Oldest Member Age",
			"fieldtype": "Int",
			"insert_after": "required_sum_insured",
		},
		{
			"fieldname": "client_type",
			"label": "Client Type",
			"fieldtype": "Select",
			"options": "Individual\nFamily\nCorporate\nSME\nGroup\nRetail",
			"insert_after": "proposer_age",
			"in_standard_filter": 1,
		},
		{
			"fieldname": "insurance_rfq_detail",
			"label": "Insurance RFQ Detail",
			"fieldtype": "Link",
			"options": "Insurance RFQ Detail",
			"insert_after": "converted_quotation",
			"read_only": 1,
		},
		{
			"fieldname": "rfq",
			"label": "ERPNext RFQ",
			"fieldtype": "Link",
			"options": "Request for Quotation",
			"insert_after": "insurance_rfq_detail",
			"read_only": 1,
		},
	],
	"Insurance Quotation": [
		{
			"fieldname": "supplier_quotation",
			"label": "Source Supplier Quotation",
			"fieldtype": "Link",
			"options": "Supplier Quotation",
			"insert_after": "provider",
			"read_only": 1,
		},
		{
			"fieldname": "insurance_rfq_detail",
			"label": "Insurance RFQ Detail",
			"fieldtype": "Link",
			"options": "Insurance RFQ Detail",
			"insert_after": "supplier_quotation",
			"read_only": 1,
		},
		{
			"fieldname": "is_selected",
			"label": "Selected by Client",
			"fieldtype": "Check",
			"insert_after": "status",
			"default": "0",
			"read_only": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
		{
			"fieldname": "premium_collection_mode",
			"label": "Premium Collection Mode",
			"fieldtype": "Select",
			"options": "Broker Collects\nDirect to Insurer",
			"insert_after": "is_selected",
			"default": "Broker Collects",
			"in_standard_filter": 1,
		},
	],
}


def ensure_custom_fields():
	"""Create the fields listed above if they do not already exist."""
	# Only create for DocTypes that actually exist on the site
	fields_to_create = {}
	for dt, fields in CUSTOM_FIELDS.items():
		if frappe.db.exists("DocType", dt):
			fields_to_create[dt] = fields
		else:
			print(f"  ⚠  DocType {dt} not found – skipping its fields")

	if fields_to_create:
		create_custom_fields(fields_to_create, update=True)
		print("  ✓ Custom fields ensured on our DocTypes")
	else:
		print("  ⚠  No target DocTypes found – custom fields skipped")


# ---------------------------------------------------------------------------
# Client Scripts
# ---------------------------------------------------------------------------

CLIENT_SCRIPTS = [
	{
		"name": "Insurance Opportunity – Create RFQ",
		"dt": "Insurance Opportunity",
		"view": "Form",
		"enabled": 1,
		"script": """
frappe.ui.form.on("Insurance Opportunity", {
	refresh(frm) {
		if (!frm.doc.insurance_rfq_detail) {
			frm.add_custom_button(__("Create RFQ & Select Insurers"), () => {
				frappe.call({
					method: "insurance_core.rfq.create_rfq_from_opportunity",
					args: { opportunity: frm.doc.name, max_insurers: 5 },
					freeze: true,
					callback(r) {
						if (r.message) {
							frm.reload_doc();
							frappe.set_route("Form", "Request for Quotation", r.message.rfq);
						}
					},
				});
			}).addClass("btn-primary");
		} else {
			frm.add_custom_button(__("Open Insurance RFQ Detail"), () => {
				frappe.set_route("Form", "Insurance RFQ Detail", frm.doc.insurance_rfq_detail);
			});
			if (frm.doc.rfq) {
				frm.add_custom_button(__("Open ERPNext RFQ"), () => {
					frappe.set_route("Form", "Request for Quotation", frm.doc.rfq);
				});
			}
		}
	},
});
""".strip(),
	},
	{
		"name": "Insurance RFQ Detail – Actions",
		"dt": "Insurance RFQ Detail",
		"view": "Form",
		"enabled": 1,
		"script": """
frappe.ui.form.on("Insurance RFQ Detail", {
	refresh(frm) {
		frm.add_custom_button(__("Re-run Insurer Selection"), () => {
			frappe.call({
				method: "insurance_core.rfq.select_insurers_on_detail",
				args: { detail_name: frm.doc.name },
				freeze: true,
				callback(r) {
					frm.reload_doc();
					frappe.show_alert({
						message: __("{0} insurer(s) selected", [r.message.insurers_added]),
						indicator: "green",
					});
				},
			});
		});

		if (frm.doc.request_for_quotation) {
			frm.add_custom_button(__("Open ERPNext RFQ"), () => {
				frappe.set_route("Form", "Request for Quotation", frm.doc.request_for_quotation);
			});
		}

		// Quick "Select as Winner" on child rows that already have a quotation
		frm.fields_dict.insurers.grid.add_custom_button(__("Select Winner"), (doc) => {
			if (!doc.insurance_quotation) {
				frappe.msgprint(__("This insurer has no Insurance Quotation yet."));
				return;
			}
			frappe.call({
				method: "insurance_core.rfq.select_winning_quote",
				args: { insurance_quotation: doc.insurance_quotation },
				freeze: true,
				callback() {
					frm.reload_doc();
				},
			});
		});
	},
});
""".strip(),
	},
]


def ensure_client_scripts():
	for cs in CLIENT_SCRIPTS:
		# Client Script requires the target DocType to exist
		if not frappe.db.exists("DocType", cs["dt"]):
			print(f"  ⚠  DocType {cs['dt']} missing – Client Script '{cs['name']}' skipped")
			continue

		existing = frappe.db.get_value("Client Script", {"name": cs["name"]}, "name")
		if existing:
			# Update script body so later improvements are picked up
			doc = frappe.get_doc("Client Script", existing)
			doc.script = cs["script"]
			doc.enabled = cs["enabled"]
			doc.save(ignore_permissions=True)
			print(f"  ✓ Client Script updated: {cs['name']}")
		else:
			doc = frappe.get_doc(
				{
					"doctype": "Client Script",
					"name": cs["name"],
					"dt": cs["dt"],
					"view": cs["view"],
					"enabled": cs["enabled"],
					"script": cs["script"],
				}
			)
			doc.insert(ignore_permissions=True)
			print(f"  ✓ Client Script created: {cs['name']}")


# ---------------------------------------------------------------------------
# Sample Insurer RFQ Rules (only if none exist)
# ---------------------------------------------------------------------------

def seed_sample_rules():
	if frappe.db.count("Insurer RFQ Rule") > 0:
		print("  ✓ Insurer RFQ Rules already present – sample seed skipped")
		return

	# Only seed if we have at least one Insurance Provider
	providers = frappe.get_all(
		"Insurance Provider",
		filters={"status": "Active"},
		pluck="name",
		limit=5,
	)
	if not providers:
		print("  ⚠  No active Insurance Providers – sample rules not created")
		return

	sample = [
		{
			"rule_name": f"Health – {providers[0]}",
			"insurance_provider": providers[0],
			"priority": 10,
			"is_active": 1,
			"line_of_business": "Health",
			"min_sum_insured": 100000,
			"max_sum_insured": 5000000,
			"require_active_agreement": 1,
		},
	]
	if len(providers) > 1:
		sample.append(
			{
				"rule_name": f"Motor – {providers[1]}",
				"insurance_provider": providers[1],
				"priority": 10,
				"is_active": 1,
				"line_of_business": "Auto",
				"min_sum_insured": 50000,
				"max_sum_insured": 2000000,
				"require_active_agreement": 1,
			}
		)

	for row in sample:
		if not frappe.db.exists("Insurer RFQ Rule", row["rule_name"]):
			frappe.get_doc({"doctype": "Insurer RFQ Rule", **row}).insert(
				ignore_permissions=True
			)
			print(f"  ✓ Sample rule created: {row['rule_name']}")


# ---------------------------------------------------------------------------
# Hooks reminder (we do not auto-edit hooks.py)
# ---------------------------------------------------------------------------

HOOKS_SNIPPET = """
# Add inside the existing doc_events dict in insurance_core/hooks.py:

doc_events = {
    # … existing entries …
    "Supplier Quotation": {
        "on_submit": "insurance_core.rfq.on_supplier_quotation_submit",
    },
}
"""


def print_hooks_reminder():
	print("\n  ── hooks.py snippet (add once) ──────────────────────────────")
	print(HOOKS_SNIPPET)
	print("  ──────────────────────────────────────────────────────────────")


# ---------------------------------------------------------------------------
# Final checklist
# ---------------------------------------------------------------------------

def print_checklist():
	print(
		"""
════════════════════════════════════════════════════════════════════════
 Broker RFQ Extension – remaining manual steps
════════════════════════════════════════════════════════════════════════

1. Place source files in the app (once):
     insurance_core/rfq.py
     insurance_core/insurance_core/doctype/insurer_rfq_rule/
     insurance_core/insurance_core/doctype/insurance_rfq_detail/
     insurance_core/insurance_core/doctype/insurance_rfq_insurer/

2. Add the hooks.py snippet printed above (Supplier Quotation on_submit).

3. Run:
     bench --site <site> migrate

4. For every Insurance Provider that should receive RFQs:
     set the field  ERPNext Supplier  →  the matching Supplier record.

5. Create / review Insurer RFQ Rules
   (sample rules may already have been seeded).

6. From an Insurance Opportunity use the button
     “Create RFQ & Select Insurers”.

════════════════════════════════════════════════════════════════════════
"""
	)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def setup(force_seed_rules: bool = False, quiet: bool = False):
	"""
	Main installer. Safe to run multiple times (idempotent).

	:param force_seed_rules: if True, always try to create sample rules
	:param quiet: if True (used from after_install/after_migrate), skip
	              verbose checklist and hooks reminder
	"""
	def log(msg: str):
		if not quiet:
			print(msg)

	log("\n▶ Broker RFQ Extension setup starting…\n")

	# 1. Fields on our DocTypes
	log("• Custom fields")
	ensure_custom_fields()

	# 2. Client Scripts
	log("• Client Scripts")
	ensure_client_scripts()

	# 3. Sample rules
	log("• Sample Insurer RFQ Rules")
	if force_seed_rules or frappe.db.count("Insurer RFQ Rule") == 0:
		seed_sample_rules()
	else:
		log("  ✓ Rules already exist")

	# 4. Reminders only when run manually
	if not quiet:
		print_hooks_reminder()
		print_checklist()

	frappe.clear_cache()
	log("▶ Setup finished.\n")


# Called from install.py after_install / after_migrate
def setup_for_hooks():
	"""Quiet entry-point for automatic install on a new site."""
	setup(quiet=True)


# Allow: bench execute …setup  (verbose, for manual runs)
def execute():
	setup(quiet=False)
