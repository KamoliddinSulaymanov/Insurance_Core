/**
 * AlfaInvest Embeddable Insurance Widget SDK (v1.0.0).
 *
 * Usage:
 * <div id="alfainvest-insurance-widget"
 *      data-scheme="KASKO_2026"
 *      data-partner="B2B-AUTO-DEALER"
 *      data-api-host="https://insurance.alfainvest.uz"></div>
 * <script src="https://insurance.alfainvest.uz/assets/insurance_core/js/widget.js" async></script>
 */

(function () {
  'use strict';

  function formatUZS(val) {
    if (!val && val !== 0) return '0';
    return Number(val).toLocaleString('ru-RU') + ' UZS';
  }

  class AlfaInvestWidget {
    constructor(container) {
      this.container = container;
      this.scheme = container.getAttribute('data-scheme') || 'KASKO';
      this.partner = container.getAttribute('data-partner') || '';
      this.apiHost = (container.getAttribute('data-api-host') || '').replace(/\/+$/, '');
      this.state = {
        loading: true,
        error: null,
        schema: null,
        theme: {
          primaryColor: '#D32F2F',
          borderRadius: '8px',
          title: 'Оформление страховки онлайн',
        },
        formData: {},
        premium: 0,
        breakdown: [],
        submitting: false,
        successPolicy: null,
      };

      this.calcTimer = null;
      this.init();
    }

    async init() {
      this.render();
      try {
        const url = `${this.apiHost}/api/method/insurance_core.widget.get_widget_bundle?scheme=${encodeURIComponent(this.scheme)}&partner=${encodeURIComponent(this.partner)}`;
        const res = await fetch(url, { headers: { Accept: 'application/json' } });
        const json = await res.json();
        if (json.exc || json.exception) {
          throw new Error(json.message || 'Ошибка загрузки параметров виджета');
        }
        const data = json.message || {};
        this.state.schema = data.order_form_schema || [];
        if (data.widget_config) {
          this.state.theme = Object.assign(this.state.theme, data.widget_config);
        }
        this.state.loading = false;

        // Initialize form data defaults
        const defaults = { sum_insured: 10000000, days: 365 };
        for (const step of this.state.schema) {
          for (const f of step.fields || []) {
            if (f.default !== undefined) {
              defaults[f.fieldname] = f.default;
            }
          }
        }
        this.state.formData = defaults;
        this.render();
        this.calculate();
      } catch (err) {
        this.state.loading = false;
        this.state.error = err.message || 'Не удалось загрузить виджет страхования';
        this.render();
      }
    }

    calculate() {
      clearTimeout(this.calcTimer);
      this.calcTimer = setTimeout(async () => {
        try {
          const url = `${this.apiHost}/api/method/insurance_core.widget.calculate_widget_premium`;
          const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              scheme: this.scheme,
              payload: this.state.formData,
            }),
          });
          const json = await res.json();
          if (json.message) {
            this.state.premium = json.message.final_premium || 0;
            this.state.breakdown = json.message.breakdown || [];
            this.updatePriceView();
          }
        } catch (e) {
          console.warn('[AlfaInvest Widget] Calc error', e);
        }
      }, 300);
    }

    async submit() {
      this.state.submitting = true;
      this.render();
      try {
        const url = `${this.apiHost}/api/method/insurance_core.widget.submit_widget_order`;
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            scheme: this.scheme,
            order_data: this.state.formData,
            partner: this.partner,
          }),
        });
        const json = await res.json();
        if (json.exc || json.exception) {
          throw new Error(json.message || 'Не удалось оформить полис');
        }
        this.state.successPolicy = json.message;
      } catch (e) {
        alert(e.message || 'Ошибка оформления');
      } finally {
        this.state.submitting = false;
        this.render();
      }
    }

    updatePriceView() {
      const priceEl = this.container.querySelector('.alfainvest-price-val');
      if (priceEl) {
        priceEl.textContent = formatUZS(this.state.premium);
      }
    }

    render() {
      const { loading, error, successPolicy, theme, formData, premium, submitting } = this.state;

      if (loading) {
        this.container.innerHTML = `
          <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 24px; text-align: center; color: #888; border: 1px solid #e2e8f0; border-radius: 8px;">
            Загрузка страхового калькулятора AlfaInvest...
          </div>
        `;
        return;
      }

      if (error) {
        this.container.innerHTML = `
          <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 16px; background: #fff5f5; color: #c53030; border: 1px solid #feb2b2; border-radius: 8px; font-size: 13px;">
            ${error}
          </div>
        `;
        return;
      }

      if (successPolicy) {
        this.container.innerHTML = `
          <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 24px; background: #fff; border: 1px solid #e2e8f0; border-radius: ${theme.borderRadius}; text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
            <div style="width: 48px; height: 48px; background: #def7ec; color: #03543f; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 24px; font-weight: bold; margin-bottom: 12px;">✓</div>
            <h3 style="margin: 0 0 8px 0; color: #1a202c; font-size: 18px;">Полис успешно оформлен!</h3>
            <p style="margin: 0 0 16px 0; font-size: 13px; color: #718096;">Номер полиса: <strong>${successPolicy.policy_number}</strong></p>
            <div style="padding: 12px; background: #f7fafc; border-radius: 6px; font-size: 14px; font-weight: bold; color: ${theme.primaryColor}; margin-bottom: 16px;">
              Премия: ${formatUZS(successPolicy.total_premium)}
            </div>
            <p style="font-size: 12px; color: #a0aec0; margin: 0;">Электронный полис выслан на контактные данные страхователя.</p>
          </div>
        `;
        return;
      }

      // Main Form Render
      const primaryColor = theme.primaryColor || '#D32F2F';

      this.container.innerHTML = `
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #fff; border: 1px solid #e2e8f0; border-radius: ${theme.borderRadius}; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); max-width: 500px; margin: 0 auto; box-sizing: border-box;">
          <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #edf2f7; padding-bottom: 12px; margin-bottom: 16px;">
            <div>
              <h3 style="margin: 0; font-size: 16px; color: #2d3748; font-weight: 700;">${theme.title || 'Онлайн страхование'}</h3>
              <span style="font-size: 11px; color: #a0aec0; text-transform: uppercase; letter-spacing: 0.5px;">AlfaInvest Partner Network</span>
            </div>
            <div style="font-size: 12px; font-weight: bold; color: ${primaryColor}; background: #fff5f5; padding: 4px 8px; border-radius: 4px;">
              ${this.scheme}
            </div>
          </div>

          <div style="margin-bottom: 16px;">
            <label style="display: block; font-size: 12px; font-weight: 600; color: #4a5568; margin-bottom: 4px;">ФИО страхователя *</label>
            <input type="text" class="alfainvest-input" data-field="full_name" value="${formData.full_name || ''}" placeholder="Иванов Иван Иванович" style="width: 100%; box-sizing: border-box; padding: 8px 12px; border: 1px solid #cbd5e0; border-radius: 6px; font-size: 13px;" />
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px;">
            <div>
              <label style="display: block; font-size: 12px; font-weight: 600; color: #4a5568; margin-bottom: 4px;">Телефон (+998) *</label>
              <input type="tel" class="alfainvest-input" data-field="phone" value="${formData.phone || '+998'}" placeholder="+998 90 123 45 67" style="width: 100%; box-sizing: border-box; padding: 8px 12px; border: 1px solid #cbd5e0; border-radius: 6px; font-size: 13px;" />
            </div>
            <div>
              <label style="display: block; font-size: 12px; font-weight: 600; color: #4a5568; margin-bottom: 4px;">ПИНФЛ (14 цифр) *</label>
              <input type="text" maxlength="14" class="alfainvest-input" data-field="pinfl" value="${formData.pinfl || ''}" placeholder="14 цифр" style="width: 100%; box-sizing: border-box; padding: 8px 12px; border: 1px solid #cbd5e0; border-radius: 6px; font-size: 13px; font-family: monospace;" />
            </div>
          </div>

          <div style="margin-bottom: 16px;">
            <label style="display: block; font-size: 12px; font-weight: 600; color: #4a5568; margin-bottom: 4px;">Страховая сумма (UZS)</label>
            <input type="number" step="1000000" class="alfainvest-input" data-field="sum_insured" value="${formData.sum_insured || 10000000}" style="width: 100%; box-sizing: border-box; padding: 8px 12px; border: 1px solid #cbd5e0; border-radius: 6px; font-size: 13px;" />
          </div>

          <div style="background: #f7fafc; border: 1px solid #edf2f7; border-radius: 6px; padding: 12px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 13px; color: #718096;">Расчетная премия:</span>
            <span class="alfainvest-price-val" style="font-size: 18px; font-weight: 800; color: ${primaryColor};">
              ${formatUZS(premium)}
            </span>
          </div>

          <button class="alfainvest-submit-btn" style="width: 100%; background: ${primaryColor}; color: #fff; border: none; padding: 12px; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; transition: opacity 0.2s;" ${submitting ? 'disabled' : ''}>
            ${submitting ? 'Оформление...' : 'Оформить полис сейчас'}
          </button>
        </div>
      `;

      // Attach event listeners
      this.container.querySelectorAll('.alfainvest-input').forEach((input) => {
        input.addEventListener('input', (e) => {
          const field = e.target.getAttribute('data-field');
          this.state.formData[field] = e.target.value;
          this.calculate();
        });
      });

      const btn = this.container.querySelector('.alfainvest-submit-btn');
      if (btn) {
        btn.addEventListener('click', () => {
          if (!this.state.formData.full_name || !this.state.formData.pinfl) {
            alert('Пожалуйста, заполните ФИО и ПИНФЛ');
            return;
          }
          this.submit();
        });
      }
    }
  }

  // Auto-initialize widgets on DOM load
  function initAlfaWidgets() {
    const el = document.getElementById('alfainvest-insurance-widget');
    if (el) {
      new AlfaInvestWidget(el);
    }
    document.querySelectorAll('.alfainvest-insurance-widget').forEach((container) => {
      new AlfaInvestWidget(container);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAlfaWidgets);
  } else {
    initAlfaWidgets();
  }

  window.AlfaInvestWidget = AlfaInvestWidget;
})();
