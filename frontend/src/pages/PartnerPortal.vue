<template>
  <div class="max-w-7xl mx-auto py-8 px-4 space-y-6">
    <!-- Header -->
    <header class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <span class="text-xs uppercase font-bold tracking-wider text-red-600 bg-red-50 px-2 py-0.5 rounded">
          B2B Партнерский портал
        </span>
        <h1 class="text-2xl font-bold text-gray-900 mt-1">
          {{ cabinet?.partner || 'Кабинет партнера' }}
        </h1>
        <p class="text-xs text-gray-500">
          Счет взаиморасчетов: <span class="font-mono font-medium text-gray-700">{{ cabinet?.account_name }}</span> ({{ cabinet?.account_type }})
        </p>
      </div>

      <div class="flex gap-2">
        <Button appearance="primary" @click="$router.push('/products')">
          + Оформить новый полис
        </Button>
      </div>
    </header>

    <!-- Financial Balance Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-white border rounded-xl p-5 shadow-sm border-l-4 border-l-green-500">
        <div class="text-xs font-semibold uppercase text-gray-500">Доступный лимит</div>
        <div class="text-2xl font-bold text-gray-900 mt-1">
          {{ formatCurrency(cabinet?.available_balance) }} <span class="text-xs text-gray-500">UZS</span>
        </div>
        <div class="text-xs text-green-600 mt-1 flex items-center gap-1 font-medium">
          <span>●</span> Готов к выписке полисов
        </div>
      </div>

      <div class="bg-white border rounded-xl p-5 shadow-sm">
        <div class="text-xs font-semibold uppercase text-gray-500">Кредитный лимит</div>
        <div class="text-2xl font-bold text-gray-900 mt-1">
          {{ formatCurrency(cabinet?.credit_limit) }} <span class="text-xs text-gray-500">UZS</span>
        </div>
        <div class="text-xs text-gray-500 mt-1">
          Овердрафт: {{ cabinet?.allow_overdraft ? formatCurrency(cabinet?.max_overdraft_amount) + ' UZS' : 'Выключен' }}
        </div>
      </div>

      <div class="bg-white border rounded-xl p-5 shadow-sm">
        <div class="text-xs font-semibold uppercase text-gray-500">Депозитный баланс</div>
        <div class="text-2xl font-bold text-gray-900 mt-1">
          {{ formatCurrency(cabinet?.deposit_balance) }} <span class="text-xs text-gray-500">UZS</span>
        </div>
        <div class="text-xs text-gray-500 mt-1">Предоплаченные средства</div>
      </div>

      <div class="bg-white border rounded-xl p-5 shadow-sm">
        <div class="text-xs font-semibold uppercase text-gray-500">Использовано лимита</div>
        <div class="text-2xl font-bold text-red-600 mt-1">
          {{ formatCurrency(cabinet?.utilized_limit) }} <span class="text-xs text-gray-500">UZS</span>
        </div>
        <div class="text-xs text-gray-500 mt-1">По оформленным договорам</div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="border-b border-gray-200">
      <nav class="flex space-x-6 text-sm font-medium">
        <button
          v-for="t in tabs"
          :key="t.id"
          @click="activeTab = t.id"
          class="pb-3 border-b-2 transition-colors"
          :class="activeTab === t.id ? 'border-red-600 text-red-600 font-semibold' : 'border-transparent text-gray-500 hover:text-gray-700'">
          {{ t.label }}
        </button>
      </nav>
    </div>

    <!-- TAB 1: Limit Ledger (Журнал движения лимитов) -->
    <div v-if="activeTab === 'ledger'" class="bg-white border rounded-xl overflow-hidden shadow-sm">
      <div class="px-6 py-4 border-b flex justify-between items-center">
        <h3 class="text-base font-semibold text-gray-900">Регистр движения баланса и лимитов (Audit Trail)</h3>
        <span class="text-xs text-gray-400">Последние 20 проводок</span>
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200 text-sm">
          <thead class="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th class="px-6 py-3 text-left">Дата</th>
              <th class="px-6 py-3 text-left">Тип операции</th>
              <th class="px-6 py-3 text-left">Документ / Референс</th>
              <th class="px-6 py-3 text-right">Списание (Дебет)</th>
              <th class="px-6 py-3 text-right">Пополнение (Кредит)</th>
              <th class="px-6 py-3 text-right">Остаток лимита</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="entry in cabinet?.ledger || []" :key="entry.name" class="hover:bg-gray-50">
              <td class="px-6 py-3 text-gray-500 font-mono text-xs whitespace-nowrap">{{ entry.posting_date }}</td>
              <td class="px-6 py-3 text-gray-900 font-medium">
                <span
                  class="inline-block px-2 py-0.5 rounded text-xs"
                  :class="entry.transaction_type.includes('Topup') ? 'bg-green-50 text-green-700' : 'bg-blue-50 text-blue-700'">
                  {{ entry.transaction_type }}
                </span>
                <div v-if="entry.remarks" class="text-xs text-gray-400 font-normal mt-0.5">{{ entry.remarks }}</div>
              </td>
              <td class="px-6 py-3 text-gray-600 font-mono text-xs">{{ entry.reference_name || '—' }}</td>
              <td class="px-6 py-3 text-right font-medium text-red-600">
                {{ entry.debit > 0 ? '-' + formatCurrency(entry.debit) + ' UZS' : '—' }}
              </td>
              <td class="px-6 py-3 text-right font-medium text-green-600">
                {{ entry.credit > 0 ? '+' + formatCurrency(entry.credit) + ' UZS' : '—' }}
              </td>
              <td class="px-6 py-3 text-right font-bold text-gray-900 font-mono text-xs">
                {{ formatCurrency(entry.balance_after) }} UZS
              </td>
            </tr>
            <tr v-if="!cabinet?.ledger?.length">
              <td colspan="6" class="px-6 py-8 text-center text-gray-400">Проводок по лимитам пока нет</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB 2: Partner Policies (Выпущенные полисы) -->
    <div v-if="activeTab === 'policies'" class="bg-white border rounded-xl overflow-hidden shadow-sm">
      <div class="px-6 py-4 border-b flex justify-between items-center">
        <h3 class="text-base font-semibold text-gray-900">Полисы, оформленные через партнера</h3>
        <Button @click="$router.push('/products')">+ Оформить полис</Button>
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200 text-sm">
          <thead class="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th class="px-6 py-3 text-left">Номер полиса</th>
              <th class="px-6 py-3 text-left">Страхователь</th>
              <th class="px-6 py-3 text-left">Продукт</th>
              <th class="px-6 py-3 text-right">Страховая премия</th>
              <th class="px-6 py-3 text-center">Статус</th>
              <th class="px-6 py-3 text-right">Действия</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="p in cabinet?.policies || []" :key="p.name" class="hover:bg-gray-50">
              <td class="px-6 py-3 font-semibold text-gray-900 font-mono text-xs">{{ p.policy_number }}</td>
              <td class="px-6 py-3 text-gray-700">{{ p.client }}</td>
              <td class="px-6 py-3 text-gray-600">{{ p.scheme }}</td>
              <td class="px-6 py-3 text-right font-medium text-gray-900">{{ formatCurrency(p.total_premium) }} UZS</td>
              <td class="px-6 py-3 text-center">
                <span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-800">
                  {{ p.status }}
                </span>
              </td>
              <td class="px-6 py-3 text-right">
                <button
                  @click="$router.push(`/policies/${p.name}`)"
                  class="text-xs text-red-600 hover:text-red-800 font-medium">
                  Открыть →
                </button>
              </td>
            </tr>
            <tr v-if="!cabinet?.policies?.length">
              <td colspan="6" class="px-6 py-8 text-center text-gray-400">Нет оформленных полисов</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB 3: Widget Generator (Встраивание виджета на сайты) -->
    <div v-if="activeTab === 'widget'" class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <!-- Widget Configuration Controls -->
      <div class="bg-white border rounded-xl p-6 shadow-sm space-y-5">
        <div>
          <h3 class="text-lg font-bold text-gray-900">Конструктор виджета для партнерских сайтов</h3>
          <p class="text-xs text-gray-500 mt-1">
            Настройте дизайн и скопируйте HTML-код для вставки на сайт вашего автосалона, банка или интернет-магазина.
          </p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Страховой продукт</label>
          <select v-model="widgetForm.scheme" class="w-full border rounded-lg px-3 py-2 text-sm bg-white">
            <option v-for="prod in cabinet?.products || []" :key="prod.scheme_id" :value="prod.scheme_id">
              {{ prod.scheme_name || prod.scheme_id }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Фирменный цвет кнопки и акцентов</label>
          <div class="flex items-center gap-3">
            <input type="color" v-model="widgetForm.color" class="h-9 w-12 rounded border p-0.5 cursor-pointer" />
            <span class="text-xs font-mono text-gray-600">{{ widgetForm.color }}</span>
            <div class="flex gap-1.5 ml-auto">
              <button
                v-for="c in presetColors"
                :key="c"
                type="button"
                @click="widgetForm.color = c"
                class="w-6 h-6 rounded-full border shadow-sm"
                :style="{ backgroundColor: c }"></button>
            </div>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Заголовок виджета</label>
          <input
            type="text"
            v-model="widgetForm.title"
            placeholder="Оформить страховку онлайн"
            class="w-full border rounded-lg px-3 py-2 text-sm" />
        </div>

        <!-- Generated Embed Code -->
        <div>
          <div class="flex justify-between items-center mb-1">
            <label class="block text-sm font-medium text-gray-700">HTML-код для вставки</label>
            <button
              type="button"
              @click="copySnippet"
              class="text-xs text-red-600 hover:text-red-800 font-medium">
              {{ copied ? 'Скопировано! ✓' : 'Копировать код' }}
            </button>
          </div>
          <pre class="bg-gray-900 text-gray-100 p-4 rounded-lg text-xs font-mono overflow-x-auto select-all leading-relaxed whitespace-pre-wrap">{{ embedSnippet }}</pre>
        </div>
      </div>

      <!-- Live Interactive Widget Preview -->
      <div class="space-y-3">
        <div class="text-xs uppercase font-semibold text-gray-400">Живой предпросмотр виджета на сайте:</div>
        <div class="border-2 border-dashed border-gray-300 rounded-2xl p-6 bg-gray-50 flex items-center justify-center">
          <div
            class="w-full max-w-sm bg-white rounded-xl shadow-lg border p-5 space-y-4"
            :style="{ borderColor: widgetForm.color }">
            <div class="flex items-center justify-between border-b pb-3">
              <div>
                <h4 class="text-sm font-bold text-gray-900">{{ widgetForm.title }}</h4>
                <span class="text-[10px] text-gray-400 uppercase tracking-wide">AlfaInvest Partner SDK</span>
              </div>
              <span
                class="text-xs font-bold px-2 py-0.5 rounded"
                :style="{ color: widgetForm.color, backgroundColor: widgetForm.color + '15' }">
                {{ widgetForm.scheme }}
              </span>
            </div>

            <div class="space-y-3 text-xs">
              <div>
                <label class="block text-gray-600 font-medium mb-1">ФИО страхователя *</label>
                <input
                  type="text"
                  placeholder="Иванов Иван Иванович"
                  class="w-full border rounded-md px-2.5 py-1.5 text-xs" />
              </div>
              <div class="grid grid-cols-2 gap-2">
                <div>
                  <label class="block text-gray-600 font-medium mb-1">Телефон *</label>
                  <input
                    type="tel"
                    placeholder="+998 90 123 45 67"
                    class="w-full border rounded-md px-2.5 py-1.5 text-xs" />
                </div>
                <div>
                  <label class="block text-gray-600 font-medium mb-1">ПИНФЛ *</label>
                  <input
                    type="text"
                    placeholder="14 цифр"
                    class="w-full border rounded-md px-2.5 py-1.5 text-xs font-mono" />
                </div>
              </div>

              <div class="bg-gray-50 border rounded-lg p-3 flex justify-between items-center">
                <span class="text-gray-500">Расчетная премия:</span>
                <span class="text-base font-extrabold" :style="{ color: widgetForm.color }">
                  1 500 000 UZS
                </span>
              </div>

              <button
                type="button"
                class="w-full py-2.5 rounded-lg text-white font-semibold text-xs transition-opacity hover:opacity-95 shadow-sm"
                :style="{ backgroundColor: widgetForm.color }">
                Оформить полис онлайн
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PartnerPortal',
  data() {
    return {
      activeTab: 'ledger',
      tabs: [
        { id: 'ledger', label: 'Движение лимитов' },
        { id: 'policies', label: 'Оформленные полисы' },
        { id: 'widget', label: 'Генератор виджета (SDK)' },
      ],
      cabinet: null,
      loading: true,
      copied: false,
      presetColors: ['#D32F2F', '#1E40AF', '#047857', '#D97706', '#7C3AED'],
      widgetForm: {
        scheme: 'KASKO_ONLINE_2026',
        color: '#D32F2F',
        title: 'Оформить страховку онлайн',
      },
    }
  },
  computed: {
    embedSnippet() {
      const origin = window.location.origin || 'https://core.alfainvest.uz'
      return `<!-- Встраиваемый виджет AlfaInvest -->\n<div id="alfainvest-insurance-widget"\n     data-scheme="${this.widgetForm.scheme}"\n     data-partner="${this.cabinet?.partner || 'B2B-PARTNER'}"\n     data-api-host="${origin}"></div>\n<script src="${origin}/assets/insurance_core/js/widget.js" async><\/script>`
    },
  },
  async created() {
    await this.fetchCabinetData()
  },
  methods: {
    formatCurrency(val) {
      if (!val && val !== 0) return '0'
      return Number(val).toLocaleString('ru-RU')
    },
    async fetchCabinetData() {
      this.loading = true
      try {
        const res = await fetch('/api/method/insurance_core.partner_limits.get_partner_cabinet_data')
        const json = await res.json()
        this.cabinet = json.message || {}
        if (this.cabinet.products && this.cabinet.products.length > 0) {
          this.widgetForm.scheme = this.cabinet.products[0].scheme_id
        }
      } catch (e) {
        console.warn('Failed to load partner cabinet', e)
      } finally {
        this.loading = false
      }
    },
    async copySnippet() {
      try {
        await navigator.clipboard.writeText(this.embedSnippet)
        this.copied = true
        setTimeout(() => (this.copied = false), 2000)
      } catch (e) {
        alert('Не удалось скопировать')
      }
    },
  },
}
</script>
