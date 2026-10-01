<template>
  <div class="max-w-6xl mx-auto py-8 px-4 space-y-6">
    <header class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Страховые продукты</h1>
        <p class="text-sm text-gray-500">
          Онлайн-оформление страховых полисов AlfaInvest
        </p>
      </div>

      <!-- LOB Filter tabs -->
      <div class="flex items-center gap-2 overflow-x-auto pb-1">
        <button
          v-for="cat in categories"
          :key="cat"
          @click="selectedCategory = cat"
          class="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap"
          :class="selectedCategory === cat ? 'bg-red-600 text-white' : 'bg-white border text-gray-600 hover:bg-gray-50'">
          {{ cat }}
        </button>
      </div>
    </header>

    <!-- Loading State -->
    <div v-if="loading" class="py-12 text-center text-gray-400">
      Загрузка витрины страховых продуктов...
    </div>

    <!-- Empty State -->
    <div v-else-if="!filteredProducts.length" class="bg-white border rounded-xl p-8 text-center text-gray-500">
      В данной категории пока нет активных продуктов.
    </div>

    <!-- Products Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="p in filteredProducts"
        :key="p.name"
        class="bg-white border rounded-xl p-6 shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow">
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-red-50 text-red-700">
              {{ p.line_of_business || 'General' }}
            </span>
            <span class="text-xs text-gray-400 font-mono">{{ p.scheme_id || p.name }}</span>
          </div>

          <h3 class="text-lg font-bold text-gray-900 leading-snug">
            {{ p.scheme_name || p.name }}
          </h3>

          <p class="text-xs text-gray-500 line-clamp-3">
            {{ p.description || 'Надежная страховая защита с оперативным оформлением и выплатами.' }}
          </p>

          <div v-if="p.minimum_sum_assured" class="pt-2 border-t text-xs text-gray-600 flex justify-between">
            <span>Страховая сумма:</span>
            <span class="font-semibold text-gray-900">от {{ formatCurrency(p.minimum_sum_assured) }} UZS</span>
          </div>
        </div>

        <div class="mt-6 pt-4 border-t flex items-center justify-between">
          <button
            @click="$router.push(`/order/${p.name}`)"
            class="w-full inline-flex justify-center items-center px-4 py-2 text-sm font-medium rounded-lg text-white bg-red-600 hover:bg-red-700 transition-colors shadow-sm">
            Оформить полис →
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Products',
  data() {
    return {
      products: [],
      loading: true,
      selectedCategory: 'Все',
      categories: ['Все', 'Автострахование', 'Имущество', 'Здоровье', 'Путешествия'],
    }
  },
  computed: {
    filteredProducts() {
      if (this.selectedCategory === 'Все') return this.products
      const map = {
        Автострахование: ['Motor', 'Auto', 'КАСКО', 'ОСАГО'],
        Имущество: ['Property', 'Fire', 'Имущество'],
        Здоровье: ['Health', 'Accident', 'Life'],
        Путешествия: ['Travel', 'Marine'],
      }
      const allowed = map[this.selectedCategory] || []
      return this.products.filter(
        (p) => allowed.includes(p.line_of_business) || allowed.some((kw) => (p.scheme_name || '').includes(kw))
      )
    },
  },
  async created() {
    await this.fetchProducts()
  },
  methods: {
    formatCurrency(val) {
      if (!val) return '0'
      return Number(val).toLocaleString('ru-RU')
    },
    async fetchProducts() {
      this.loading = true
      try {
        const res = await fetch('/api/method/insurance_core.api.get_active_schemes')
        const json = await res.json()
        this.products = json.message || []
      } catch (e) {
        console.warn('Failed to load schemes', e)
      } finally {
        this.loading = false
      }
    },
  },
}
</script>
