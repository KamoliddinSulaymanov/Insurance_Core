# Copyright (c) 2026, Vivaswan Works and contributors
# License: MIT
"""
Installer for Policy PDF Upload + Parse feature.

Run after DocType files and policy_pdf_parser.py are in the app:

    bench --site <site> execute insurance_core.policy_upload.install_policy_upload.setup

Or:

    from insurance_core.policy_upload.install_policy_upload import setup
    setup()

What this does
--------------
1. Creates custom fields on Insurance Policy for T&Cs, claim eligibility, exclusions,
   parsed_from_pdf flag, and link back to Policy Upload.
2. Ensures Client Script for Policy Upload form (Parse + Create buttons).
3. Prints remaining checklist (copy files, migrate, optional pdfplumber).
"""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


CUSTOM_FIELDS = {
	"Insurance Policy": [
		{
			"fieldname": "section_policy_wordings",
			"label": "Policy Wordings & Claim Eligibility",
			"fieldtype": "Section Break",
			"insert_after": "other_documents",
			"collapsible": 1,
		},
		{
			"fieldname": "terms_and_conditions",
			"label": "Terms & Conditions",
			"fieldtype": "Text Editor",
			"insert_after": "section_policy_wordings",
			"description": "Full policy T&Cs – used by AI agent when comparing claim vs policy.",
		},
		{
			"fieldname": "claim_eligibility_rules",
			"label": "Claim Eligibility / Conditions",
			"fieldtype": "Text Editor",
			"insert_after": "terms_and_conditions",
			"description": "Claim intimation timelines, required documents, waiting periods, cashless rules, etc.",
		},
		{
			"fieldname": "policy_exclusions",
			"label": "Exclusions",
			"fieldtype": "Text Editor",
			"insert_after": "claim_eligibility_rules",
		},
		{
			"fieldname": "parsed_from_pdf",
			"label": "Parsed from PDF",
			"fieldtype": "Check",
			"insert_after": "policy_exclusions",
			"read_only": 1,
			"default": "0",
		},
		{
			"fieldname": "source_policy_upload",
			"label": "Source Policy Upload",
			"fieldtype": "Link",
			"options": "Policy Upload",
			"insert_after": "parsed_from_pdf",
			"read_only": 1,
		},
	],
}


CLIENT_SCRIPT_NAME = "Policy Upload – Parse & Create"
CLIENT_SCRIPT = r"""
frappe.ui.form.on('Policy Upload', {
	refresh(frm) {
		frm.disable_save = false;

		if (frm.doc.policy_pdf && !['Policy Created', 'Cancelled'].includes(frm.doc.status)) {
			frm.add_custom_button(__('Parse PDF'), () => {
				frappe.call({
					method: 'insurance_core.insurance_core.doctype.policy_upload.policy_upload.parse_policy_pdf',
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __('Parsing policy PDF…'),
					callback(r) {
						if (r.message && r.message.ok) {
							frappe.show_alert({ message: r.message.message, indicator: 'green' });
							frm.reload_doc();
						}
					}
				});
			}, __('Actions'));
		}

		if (frm.doc.status === 'Parsed' || frm.doc.status === 'Client Linked') {
			frm.add_custom_button(__('Create Client & Policy'), () => {
				frappe.confirm(
					__('Create Insurance Client (if new) and Insurance Policy from the extracted data?'),
					() => {
						frappe.call({
							method: 'insurance_core.insurance_core.doctype.policy_upload.policy_upload.create_client_and_policy',
							args: { name: frm.doc.name },
							freeze: true,
							freeze_message: __('Creating client & policy…'),
							callback(r) {
								if (r.message && r.message.ok) {
									frappe.show_alert({ message: r.message.message, indicator: 'green' });
									frm.reload_doc();
									if (r.message.policy) {
										frappe.set_route('Form', 'Insurance Policy', r.message.policy);
									}
								}
							}
						});
					}
				);
			}, __('Actions')).addClass('btn-primary');
		}

		if (frm.doc.created_policy) {
			frm.add_custom_button(__('Open Policy'), () => {
				frappe.set_route('Form', 'Insurance Policy', frm.doc.created_policy);
			});
		}
		if (frm.doc.created_client) {
			frm.add_custom_button(__('Open Client'), () => {
				frappe.set_route('Form', 'Insurance Client', frm.doc.created_client);
			});
		}
	},

	client_mode(frm) {
		frm.toggle_reqd('existing_client', frm.doc.client_mode === 'Existing Client');
		frm.toggle_reqd('new_client_name', frm.doc.client_mode === 'Create New Client');
	},

	policy_pdf(frm) {
		if (frm.doc.policy_pdf && frm.doc.status === 'Draft') {
			frm.set_value('parse_status', __('PDF attached. Save and click Parse PDF.'));
		}
	}
});
"""


def setup():
	"""Entry point for bench execute."""
	frappe.flags.in_install = True
	try:
		_create_fields()
		_ensure_client_script()
		_print_checklist()
	finally:
		frappe.flags.in_install = False


def _create_fields():
	create_custom_fields(CUSTOM_FIELDS, update=True)
	print("✓ Custom fields on Insurance Policy (T&Cs, claim eligibility, exclusions, parsed_from_pdf)")


def _ensure_client_script():
	name = CLIENT_SCRIPT_NAME
	if frappe.db.exists("Client Script", name):
		cs = frappe.get_doc("Client Script", name)
		cs.script = CLIENT_SCRIPT
		cs.enabled = 1
		cs.save(ignore_permissions=True)
		print(f"✓ Updated Client Script: {name}")
	else:
		cs = frappe.get_doc(
			{
				"doctype": "Client Script",
				"name": name,
				"dt": "Policy Upload",
				"view": "Form",
				"enabled": 1,
				"script": CLIENT_SCRIPT,
			}
		)
		cs.insert(ignore_permissions=True)
		print(f"✓ Created Client Script: {name}")


def _print_checklist():
	print(
		"""
============================================================
 Policy Upload – remaining checklist
============================================================
1. Copy package into the app (once):

   # DocType
   mkdir -p apps/insurance_core/insurance_core/doctype/policy_upload
   cp policy_upload/doctype/policy_upload/* \\
      apps/insurance_core/insurance_core/doctype/policy_upload/

   # Parser module
   cp policy_upload/policy_pdf_parser.py \\
      apps/insurance_core/insurance_core/policy_pdf_parser.py

   # Installer (optional subpackage)
   mkdir -p apps/insurance_core/insurance_core/policy_upload
   cp policy_upload/install_policy_upload.py \\
      apps/insurance_core/insurance_core/policy_upload/
   touch apps/insurance_core/insurance_core/policy_upload/__init__.py

2. Optional but recommended – better PDF text extraction:
   bench pip install pdfplumber
   # or: pip install pdfplumber  (in the bench env)

3. Migrate & re-run installer:
   bench --site <site> migrate
   bench --site <site> execute insurance_core.policy_upload.install_policy_upload.setup
   bench --site <site> clear-cache

4. Desk usage:
   - New → Policy Upload
   - Attach policy PDF
   - Choose Existing Client OR Create New Client
   - Actions → Parse PDF
   - Review / correct extracted fields, map Provider + Scheme
   - Actions → Create Client & Policy

5. Fields stored on Insurance Policy for AI claim comparison later:
   - terms_and_conditions
   - claim_eligibility_rules
   - policy_exclusions
   - parsed_from_pdf
   - source_policy_upload

============================================================
"""
	)


if __name__ == "__main__":
	setup()
