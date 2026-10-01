frappe.ui.form.on('Insurance Scheme', {
	refresh(frm) {
		if (frm.is_new()) return;

		// 1. Sandbox Calculation (Dynamic No-Code Engine)
		frm.add_custom_button(__('Тестовый расчет (Sandbox)'), () => {
			frappe.call({
				method: 'insurance_core.order_engine.get_order_schema',
				args: { scheme: frm.doc.name },
				callback(r) {
					if (!r.message) return;
					const schema = r.message.order_form_schema || [];
					const dialogFields = [];

					// Flatten schema fields for testing in dialog
					for (const step of schema) {
						for (const f of step.fields || []) {
							dialogFields.push({
								fieldname: f.fieldname,
								label: f.label || f.fieldname,
								fieldtype: f.type === 'Number' ? 'Float' : f.type === 'Select' ? 'Select' : 'Data',
								options: f.options ? (Array.isArray(f.options) ? f.options.join('\n') : f.options) : '',
								default: f.default || '',
								reqd: f.required ? 1 : 0,
							});
						}
					}

					if (!dialogFields.length) {
						dialogFields.push(
							{ fieldname: 'sum_insured', label: __('Страховая сумма (UZS)'), fieldtype: 'Currency', default: 10000000 },
							{ fieldname: 'days', label: __('Срок (дней)'), fieldtype: 'Int', default: 365 }
						);
					}

					const d = new frappe.ui.Dialog({
						title: __('Тестирование расчета: ') + (frm.doc.scheme_name || frm.doc.name),
						fields: dialogFields,
						primary_action_label: __('Рассчитать премию'),
						primary_action(values) {
							frappe.call({
								method: 'insurance_core.order_engine.calculate_order_premium',
								args: {
									scheme: frm.doc.name,
									form_data: values,
								},
								callback(res) {
									if (!res.message) return;
									const calc = res.message;
									const breakdownHtml = (calc.breakdown || [])
										.map((b) => `<li style="font-family: monospace; font-size: 11px;">${b}</li>`)
										.join('');

									frappe.msgprint({
										title: __('Результат расчета премии'),
										indicator: 'green',
										message: `
											<div style="font-size: 14px; margin-bottom: 8px;">
												<strong>Итоговая премия:</strong> <span style="font-size: 18px; color: #D32F2F; font-weight: bold;">${(calc.final_premium || 0).toLocaleString('ru-RU')} UZS</span>
											</div>
											<div style="font-size: 12px; color: #666; margin-bottom: 8px;">
												Базовая премия: ${(calc.base_premium || 0).toLocaleString('ru-RU')} UZS
											</div>
											<div style="margin-top: 10px; border-top: 1px solid #eee; padding-top: 8px;">
												<strong>Декомпозиция (Breakdown):</strong>
												<ul style="margin: 4px 0 0 16px; padding: 0;">${breakdownHtml}</ul>
											</div>
										`,
									});
								},
							});
						},
					});
					d.show();
				},
			});
		}, __('Действия'));

		// 2. Export Product JSON Bundle
		frm.add_custom_button(__('Экспорт бандла (JSON)'), () => {
			frappe.call({
				method: 'insurance_core.product_factory.export_product_bundle',
				args: { scheme_name: frm.doc.name },
				callback(r) {
					if (!r.message) return;
					const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(r.message, null, 2));
					const dlAnchor = document.createElement('a');
					dlAnchor.setAttribute('href', dataStr);
					dlAnchor.setAttribute('download', `${frm.doc.name}_bundle.json`);
					dlAnchor.click();
					frappe.show_alert({ message: __('Бандл продукта экспортирован'), indicator: 'green' });
				},
			});
		}, __('Действия'));

		// 3. Electronic Signature / Sign Product
		if (frm.doc.status === 'Draft' || frm.doc.status === 'Under Review') {
			frm.add_custom_button(__('Подписать продукт (ЭЦП / Виза)'), () => {
				frappe.confirm(
					__('Подписать конфигурацию продукта от имени текущего пользователя?'),
					() => {
						frappe.call({
							method: 'insurance_core.product_factory.sign_product',
							args: { scheme_name: frm.doc.name },
							callback() {
								frm.reload_doc();
								frappe.show_alert({ message: __('Продукт успешно подписан'), indicator: 'green' });
							},
						});
					}
				);
			}, __('Действия'));
		}

		// 4. Publish Product
		if (frm.doc.status === 'Signed') {
			frm.add_custom_button(__('Опубликовать продукт'), () => {
				frappe.confirm(
					__('Опубликовать продукт для продаж во всех каналах и партнерской сети?'),
					() => {
						frappe.call({
							method: 'insurance_core.product_factory.publish_product',
							args: { scheme_name: frm.doc.name },
							callback() {
								frm.reload_doc();
								frappe.show_alert({ message: __('Продукт опубликован'), indicator: 'green' });
							},
						});
					}
				);
			}, __('Действия'));
		}

		// 5. Locking / Unlocking
		if (frm.doc.is_locked) {
			frm.add_custom_button(__('Снять блокировку редактирования'), () => {
				frappe.call({
					method: 'insurance_core.product_factory.unlock_product',
					args: { scheme_name: frm.doc.name },
					callback() {
						frm.reload_doc();
						frappe.show_alert({ message: __('Блокировка снята'), indicator: 'blue' });
					},
				});
			}, __('Безопасность'));
		} else {
			frm.add_custom_button(__('Заблокировать для редактирования'), () => {
				frappe.call({
					method: 'insurance_core.product_factory.lock_product',
					args: { scheme_name: frm.doc.name },
					callback() {
						frm.reload_doc();
						frappe.show_alert({ message: __('Продукт заблокирован для вашей сессии'), indicator: 'blue' });
					},
				});
			}, __('Безопасность'));
		}
	},
});
