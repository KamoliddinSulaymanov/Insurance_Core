frappe.ui.form.on('Partner Credit Account', {
	refresh(frm) {
		if (frm.is_new()) return;

		// 1. Quick Deposit Topup
		frm.add_custom_button(__('Пополнить депозит'), () => {
			const d = new frappe.ui.Dialog({
				title: __('Пополнение депозитного баланса'),
				fields: [
					{
						fieldname: 'amount',
						label: __('Сумма пополнения (UZS)'),
						fieldtype: 'Currency',
						reqd: 1,
					},
					{
						fieldname: 'reference',
						label: __('Номер банковского платежного поручения'),
						fieldtype: 'Data',
						reqd: 1,
					},
					{
						fieldname: 'remarks',
						label: __('Примечание'),
						fieldtype: 'Small Text',
					},
				],
				primary_action_label: __('Провести пополнение'),
				primary_action(vals) {
					frappe.call({
						method: 'frappe.client.insert',
						args: {
							doc: {
								doctype: 'Partner Limit Ledger',
								account: frm.doc.name,
								partner: frm.doc.partner,
								posting_date: frappe.datetime.now_datetime(),
								transaction_type: 'Deposit Topup',
								reference_doctype: 'Bank Transaction',
								reference_name: vals.reference,
								credit: vals.amount,
								debit: 0.0,
								remarks: vals.remarks || 'Пополнение депозитного счета',
							},
						},
						callback() {
							// Update partner credit account deposit balance
							frappe.db.set_value(
								'Partner Credit Account',
								frm.doc.name,
								'deposit_balance',
								(frm.doc.deposit_balance || 0) + vals.amount
							).then(() => {
								frm.reload_doc();
								d.hide();
								frappe.show_alert({ message: __('Депозитный баланс успешно пополнен'), indicator: 'green' });
							});
						},
					});
				},
			});
			d.show();
		}, __('Действия'));

		// 2. Open Partner Portal
		frm.add_custom_button(__('Открыть в B2B Кабинете'), () => {
			window.open(`/insurance_core/partner?partner=${encodeURIComponent(frm.doc.partner || '')}`, '_blank');
		}, __('Действия'));
	},
});
