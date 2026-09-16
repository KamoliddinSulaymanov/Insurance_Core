// Client Script equivalent – also installed via install_policy_upload.py
// DocType: Policy Upload

frappe.ui.form.on('Policy Upload', {
	refresh(frm) {
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
