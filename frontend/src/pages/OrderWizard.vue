<template>
  <div class="max-w-6xl mx-auto py-8 px-4">
    <!-- Header -->
    <div class="mb-6 flex items-center justify-between">
      <div>
        <button
          v-if="currentStep < 4"
          @click="$router.push('/products')"
          class="text-xs text-gray-500 hover:text-gray-800 flex items-center gap-1 mb-1">
          ← К каталогу продуктов
        </button>
        <h1 class="text-2xl font-bold text-gray-900">
          {{ product?.scheme_name || 'Оформление страхового полиса' }}
        </h1>
        <p class="text-sm text-gray-500">
          {{ product?.provider }} · {{ product?.line_of_business }}
        </p>
      </div>

      <!-- Step Indicator -->
      <div v-if="currentStep < 4" class="hidden sm:flex items-center gap-2">
        <div
          v-for="s in totalSteps"
          :key="s"
          class="flex items-center gap-2">
          <div
            class="w-7 h-7 rounded-full text-xs font-semibold flex items-center justify-center transition-colors"
            :class="s === currentStep ? 'bg-red-600 text-white' : s < currentStep ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-600'">
            {{ s < currentStep ? '✓' : s }}
          </div>
          <span v-if="s < totalSteps" class="w-6 h-0.5 bg-gray-200"></span>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loadingProduct" class="py-12 text-center text-gray-500">
      Загрузка параметров продукта...
    </div>

    <!-- Error State -->
    <div v-else-if="loadError" class="rounded-lg bg-red-50 p-4 text-sm text-red-700">
      {{ loadError }}
    </div>

    <!-- Wizard Body -->
    <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Left 2 Cols: Step Content -->
      <div class="lg:col-span-2 space-y-6">
        <!-- STEP 1 to N-1: Dynamic Schema Steps -->
        <div
          v-if="currentStep <= schemaSteps.length"
          class="bg-white border rounded-xl p-6 shadow-sm">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">
            {{ activeStepConfig?.step_title || `Шаг ${currentStep}` }}
          </h2>

          <SchemaFormRenderer
            :fields="activeStepConfig?.fields || []"
            v-model="formData"
            @change="onFormChange" />

          <div class="mt-6 flex justify-between items-center pt-4 border-t">
            <button
              v-if="currentStep > 1"
              type="button"
              @click="currentStep--"
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
              Назад
            </button>
            <div v-else></div>

            <Button
              appearance="primary"
              @click="goToNextStep">
              Далее →
            </Button>
          </div>
        </div>

        <!-- STEP: Payment & Agreements -->
        <div
          v-else-if="currentStep === schemaSteps.length + 1"
          class="bg-white border rounded-xl p-6 shadow-sm space-y-6">
          <h2 class="text-lg font-semibold text-gray-900">
            Оплата и подтверждение выпуска
          </h2>

          <!-- Payment Options -->
          <div class="space-y-3">
            <label class="block text-sm font-medium text-gray-700">
              Выберите способ оплаты страховой премии
            </label>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label
                v-for="plan in paymentPlans"
                :key="plan.id"
                class="flex items-start gap-3 p-3 border rounded-lg cursor-pointer transition-all hover:border-red-400"
                :class="selectedPlan === plan.id ? 'border-red-600 bg-red-50/30 ring-1 ring-red-600' : 'border-gray-200'">
                <input
                  type="radio"
                  name="paymentPlan"
                  :value="plan.id"
                  v-model="selectedPlan"
                  class="mt-1 h-4 w-4 text-red-600 focus:ring-red-500" />
                <div>
                  <div class="text-sm font-medium text-gray-900">{{ plan.title }}</div>
                  <div class="text-xs text-gray-500">{{ plan.description }}</div>
                </div>
              </label>
            </div>
          </div>

          <!-- Installment Preview Table (if installment selected) -->
          <div v-if="installmentsPreview.length > 1" class="border rounded-lg overflow-hidden">
            <div class="bg-gray-50 px-4 py-2 text-xs font-semibold text-gray-600 uppercase">
              График взносов рассрочки
            </div>
            <table class="min-w-full divide-y divide-gray-200 text-sm">
              <thead class="bg-gray-50/50 text-xs text-gray-500">
                <tr>
                  <th class="px-4 py-2 text-left">Транш</th>
                  <th class="px-4 py-2 text-left">Срок оплаты</th>
                  <th class="px-4 py-2 text-right">Сумма к оплате</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                <tr v-for="inst in installmentsPreview" :key="inst.installment_number">
                  <td class="px-4 py-2 text-gray-700">Платеж #{{ inst.installment_number }}</td>
                  <td class="px-4 py-2 text-gray-600">{{ inst.due_date }}</td>
                  <td class="px-4 py-2 text-right font-medium text-gray-900">
                    {{ formatCurrency(inst.amount) }} UZS
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Agreements Checkbox -->
          <div class="pt-2">
            <label class="flex items-start gap-2 cursor-pointer">
              <input
                type="checkbox"
                v-model="termsAccepted"
                class="mt-1 h-4 w-4 rounded border-gray-300 text-red-600 focus:ring-red-500" />
              <span class="text-xs text-gray-600 leading-snug">
                Я подтверждаю достоверность указанных данных и согласен с
                <a href="#" class="text-red-600 hover:underline">Правилами страхования</a>
                и условиями публичной оферты AlfaInvest.
              </span>
            </label>
          </div>

          <div v-if="submitError" class="p-3 bg-red-50 rounded-lg text-xs text-red-700">
            {{ submitError }}
          </div>

          <!-- Action Buttons -->
          <div class="flex justify-between items-center pt-4 border-t">
            <button
              type="button"
              @click="currentStep--"
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
              Назад
            </button>

            <Button
              appearance="primary"
              :loading="submitting"
              :disabled="!termsAccepted"
              @click="submitOrder">
              Оформить и оплатить полис
            </Button>
          </div>
        </div>

        <!-- STEP: Success / Receipt Screen -->
        <div
          v-else-if="currentStep === totalSteps"
          class="bg-white border rounded-xl p-8 shadow-sm space-y-6 text-center">
          <div class="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto text-2xl font-bold">
            ✓
          </div>

          <div>
            <h2 class="text-2xl font-bold text-gray-900">Полис успешно оформлен!</h2>
            <p class="text-sm text-gray-500 mt-1">
              Договор страхования зарегистрирован в учетной системе.
            </p>
          </div>

          <div class="bg-gray-50 rounded-xl p-4 max-w-md mx-auto text-left space-y-2 border">
            <div class="flex justify-between text-sm">
              <span class="text-gray-500">Номер полиса:</span>
              <span class="font-bold text-gray-900">{{ issuedPolicy?.policy_number }}</span>
            </div>
            <div v-if="issuedPolicy?.eois_number" class="flex justify-between text-sm">
              <span class="text-gray-500">Реестр ЕОИС РУз:</span>
              <span class="font-mono text-xs font-semibold text-gray-700">{{ issuedPolicy.eois_number }}</span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-gray-500">Страхователь:</span>
              <span class="font-medium text-gray-800">{{ formData.full_name || issuedPolicy?.client }}</span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-gray-500">Итоговая премия:</span>
              <span class="font-bold text-red-600">{{ formatCurrency(calculatedPremium) }} UZS</span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-gray-500">Статус:</span>
              <span class="px-2 py-0.5 rounded text-xs font-semibold bg-green-100 text-green-800">
                {{ issuedPolicy?.status || 'Active' }}
              </span>
            </div>

            <!-- Digital QR Code -->
            <div v-if="issuedPolicy?.qr_svg" class="pt-3 border-t flex flex-col items-center justify-center">
              <div class="w-36 h-36" v-html="issuedPolicy.qr_svg" />
              <a
                v-if="issuedPolicy?.verification_url"
                :href="issuedPolicy.verification_url"
                target="_blank"
                class="text-xs text-red-600 hover:underline mt-1 font-medium">
                Проверить подлинность в ЕОИС →
              </a>
            </div>
          </div>

          <div class="flex justify-center gap-3 pt-4">
            <Button
              appearance="primary"
              @click="$router.push(`/policies/${issuedPolicy?.policy_name || ''}`)">
              Просмотреть полис
            </Button>
            <a
              v-if="issuedPolicy?.policy_name"
              :href="`/api/method/frappe.utils.print_format.download_pdf?doctype=Insurance+Policy&name=${issuedPolicy.policy_name}&format=Standard`"
              target="_blank"
              class="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
              Скачать PDF
            </a>
            <Button
              @click="$router.push('/products')">
              К каталогу продуктов
            </Button>
          </div>
        </div>
      </div>

      <!-- Right 1 Col: Calculation Summary Sidebar -->
      <div v-if="currentStep < totalSteps" class="space-y-4">
        <div class="bg-white border rounded-xl p-5 shadow-sm sticky top-20 space-y-4">
          <div class="border-b pb-3">
            <div class="text-xs uppercase tracking-wider text-gray-400 font-semibold">
              Расчет страховой премии
            </div>
            <div class="text-3xl font-extrabold text-red-600 mt-1">
              {{ formatCurrency(calculatedPremium) }} <span class="text-sm font-normal text-gray-500">UZS</span>
            </div>
            <div v-if="calculating" class="text-xs text-gray-400 mt-1 animate-pulse">
              Пересчет тарифов...
            </div>
          </div>

          <!-- Actuarial Breakdown Details -->
          <div v-if="breakdown.length" class="space-y-2">
            <div class="text-xs font-semibold text-gray-600">Детализация расчета (Breakdown):</div>
            <ul class="text-xs text-gray-600 space-y-1.5 font-mono bg-gray-50 p-3 rounded-lg border">
              <li
                v-for="(item, idx) in breakdown"
                :key="idx"
                class="leading-tight">
                {{ item }}
              </li>
            </ul>
          </div>

          <div class="text-xs text-gray-400 border-t pt-3">
            Расчет выполняется автоматическим No-Code движком тарифов AlfaInvest на основе параметров заказа.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import SchemaFormRenderer from '@/components/SchemaFormRenderer.vue'

export default {
  name: 'OrderWizard',
  components: {
    SchemaFormRenderer,
  },
  data() {
    return {
      schemeName: this.$route.params.scheme || '',
      loadingProduct: true,
      loadError: '',
      product: null,
      schemaSteps: [],
      currentStep: 1,
      formData: {},
      calculating: false,
      calculatedPremium: 0,
      breakdown: [],
      calcTimer: null,
      selectedPlan: '100% Full Payment',
      termsAccepted: false,
      submitting: false,
      submitError: '',
      issuedPolicy: null,
      paymentPlans: [
        { id: '100% Full Payment', title: '100% Оплата онлайн', description: 'Единоразовый платеж всей суммы премии' },
        { id: '50/50 Split', title: 'Рассрочка 50/50', description: '2 платежа: первый сейчас, второй через 3 месяца' },
        { id: 'Quarterly (4x25%)', title: 'Ежеквартальная (4 взноса)', description: '4 равных транша каждые 3 месяца' },
        { id: 'Partner Credit Account', title: 'Партнерский лимит B2B', description: 'Безналичное списание с кредитного лимита' },
      ],
    }
  },
  computed: {
    totalSteps() {
      // Schema steps + Payment step + Receipt step
      return this.schemaSteps.length + 2
    },
    activeStepConfig() {
      return this.schemaSteps[this.currentStep - 1]
    },
    installmentsPreview() {
      if (!this.calculatedPremium || this.selectedPlan === '100% Full Payment') {
        return [{ installment_number: 1, due_date: 'Сегодня', amount: this.calculatedPremium }]
      }
      if (this.selectedPlan === '50/50 Split') {
        const half = Math.round((this.calculatedPremium / 2) * 100) / 100
        return [
          { installment_number: 1, due_date: 'Сегодня', amount: half },
          { installment_number: 2, due_date: 'Через 90 дней', amount: Math.round((this.calculatedPremium - half) * 100) / 100 },
        ]
      }
      if (this.selectedPlan === 'Quarterly (4x25%)') {
        const part = Math.round((this.calculatedPremium / 4) * 100) / 100
        return [
          { installment_number: 1, due_date: 'Сегодня', amount: part },
          { installment_number: 2, due_date: 'Через 90 дней', amount: part },
          { installment_number: 3, due_date: 'Через 180 дней', amount: part },
          { installment_number: 4, due_date: 'Через 270 дней', amount: Math.round((this.calculatedPremium - part * 3) * 100) / 100 },
        ]
      }
      return [{ installment_number: 1, due_date: 'Сегодня', amount: this.calculatedPremium }]
    },
  },
  async created() {
    await this.fetchProductSchema()
  },
  methods: {
    formatCurrency(val) {
      if (!val && val !== 0) return '0'
      return Number(val).toLocaleString('ru-RU')
    },
    async fetchProductSchema() {
      this.loadingProduct = true
      this.loadError = ''
      try {
        const res = await fetch(
          `/api/method/insurance_core.order_engine.get_order_schema?scheme=${encodeURIComponent(this.schemeName)}`
        )
        const json = await res.json()
        if (json.exc || json.exception) {
          throw new Error(json.message || 'Ошибка загрузки продукта')
        }
        this.product = json.message
        this.schemaSteps = this.product.order_form_schema || []

        // Set defaults from schema
        const initial = {}
        for (const step of this.schemaSteps) {
          for (const f of step.fields || []) {
            if (f.default !== undefined) {
              initial[f.fieldname] = f.default
            }
          }
        }
        this.formData = initial
        this.triggerCalculation()
      } catch (e) {
        this.loadError = e.message || 'Не удалось загрузить конфигурацию продукта'
      } finally {
        this.loadingProduct = false
      }
    },
    onFormChange() {
      this.triggerCalculation()
    },
    triggerCalculation() {
      clearTimeout(this.calcTimer)
      this.calcTimer = setTimeout(async () => {
        this.calculating = true
        try {
          const res = await fetch('/api/method/insurance_core.order_engine.calculate_order_premium', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              scheme: this.schemeName,
              form_data: this.formData,
            }),
          })
          const json = await res.json()
          if (json.message) {
            this.calculatedPremium = json.message.final_premium || 0
            this.breakdown = json.message.breakdown || []
          }
        } catch (e) {
          console.warn('Calculation error', e)
        } finally {
          this.calculating = false
        }
      }, 300)
    },
    goToNextStep() {
      // Basic check for required fields of current step
      const currentFields = this.activeStepConfig?.fields || []
      for (const f of currentFields) {
        if (f.required && (this.formData[f.fieldname] === undefined || this.formData[f.fieldname] === '')) {
          alert(`Пожалуйста, заполните обязательное поле "${f.label || f.fieldname}"`)
          return
        }
      }
      this.currentStep++
    },
    async submitOrder() {
      this.submitting = true
      this.submitError = ''
      try {
        const res = await fetch('/api/method/insurance_core.order_engine.submit_order', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            scheme: this.schemeName,
            form_data: this.formData,
            payment_method: this.selectedPlan,
          }),
        })
        const json = await res.json()
        if (json.exc || json.exception) {
          throw new Error(json.message || 'Ошибка оформления заказа')
        }
        this.issuedPolicy = json.message
        this.currentStep = this.totalSteps
      } catch (e) {
        this.submitError = e.message || 'Ошибка оформления полиса'
      } finally {
        this.submitting = false
      }
    },
  },
}
</script>
