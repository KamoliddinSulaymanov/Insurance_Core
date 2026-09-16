// Copyright (c) 2026, Vivaswan Works and contributors
// License: MIT

frappe.ui.form.on("Insurance Provider API", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Test Connection"), () => {
				frappe.call({
					method: "insurance_core.insurance_core.doctype.insurance_provider_api.insurance_provider_api.test_connection",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Testing connection…"),
					callback(r) {
						frm.reload_doc();
						if (!r.message) return;
						const ok = r.message.status === "Success";
						frappe.msgprint({
							title: ok ? __("Connection OK") : __("Connection Failed"),
							indicator: ok ? "green" : "red",
							message: ok
								? __("Reached {0} (HTTP {1})", [
										r.message.url,
										r.message.http_status || "—",
								  ])
								: r.message.error || __("Unknown error"),
						});
					},
				});
			}).addClass("btn-primary");
		}
	},
});
