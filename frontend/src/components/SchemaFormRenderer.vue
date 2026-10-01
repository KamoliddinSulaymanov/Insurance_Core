<template>
  <div class="space-y-4">
    <div
      v-for="field in visibleFields"
      :key="field.fieldname"
      class="space-y-1">
      <label class="block text-sm font-medium text-gray-700">
        {{ field.label || field.fieldname }}
        <span v-if="field.required" class="text-red-500">*</span>
      </label>

      <!-- Select field -->
      <select
        v-if="isSelect(field)"
        :value="modelValue[field.fieldname]"
        @change="updateField(field.fieldname, $event.target.value)"
        class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500">
        <option value="" disabled>{{ field.placeholder || 'Выберите значение' }}</option>
        <option
          v-for="opt in getOptions(field)"
          :key="opt.value"
          :value="opt.value">
          {{ opt.label }}
        </option>
      </select>

      <!-- Boolean / Checkbox -->
      <div v-else-if="isCheck(field)" class="flex items-center gap-2 pt-1">
        <input
          type="checkbox"
          :checked="!!modelValue[field.fieldname]"
          @change="updateField(field.fieldname, $event.target.checked ? 1 : 0)"
          class="h-4 w-4 rounded border-gray-300 text-red-600 focus:ring-red-500" />
        <span class="text-xs text-gray-500">{{ field.description || field.label }}</span>
      </div>

      <!-- Textarea -->
      <textarea
        v-else-if="isTextarea(field)"
        :value="modelValue[field.fieldname]"
        @input="updateField(field.fieldname, $event.target.value)"
        :rows="field.rows || 3"
        :placeholder="field.placeholder || ''"
        class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500" />

      <!-- Number -->
      <input
        v-else-if="isNumber(field)"
        type="number"
        :value="modelValue[field.fieldname]"
        @input="updateField(field.fieldname, $event.target.value === '' ? '' : Number($event.target.value))"
        :min="field.min"
        :max="field.max"
        :step="field.step || 'any'"
        :placeholder="field.placeholder || ''"
        class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500" />

      <!-- Date -->
      <input
        v-else-if="isDate(field)"
        type="date"
        :value="modelValue[field.fieldname]"
        @input="updateField(field.fieldname, $event.target.value)"
        class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500" />

      <!-- PINFL (14 digits) -->
      <div v-else-if="isPinfl(field)" class="relative">
        <input
          type="text"
          maxlength="14"
          :value="modelValue[field.fieldname]"
          @input="onPinflInput(field.fieldname, $event.target.value)"
          placeholder="14 цифр ПИНФЛ (ЖШШИР)"
          class="w-full rounded-md border px-3 py-2 text-sm font-mono tracking-wider shadow-sm focus:outline-none focus:ring-1"
          :class="pinflError ? 'border-red-400 focus:border-red-500 focus:ring-red-500' : 'border-gray-300 focus:border-red-500 focus:ring-red-500'" />
        <span v-if="pinflError" class="text-xs text-red-500 block mt-1">{{ pinflError }}</span>
      </div>

      <!-- Phone (+998 mask helper) -->
      <div v-else-if="isPhone(field)" class="relative">
        <input
          type="tel"
          :value="modelValue[field.fieldname]"
          @input="onPhoneInput(field.fieldname, $event.target.value)"
          placeholder="+998 90 123 45 67"
          class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500" />
      </div>

      <!-- Standard text input (default) -->
      <input
        v-else
        type="text"
        :value="modelValue[field.fieldname]"
        @input="updateField(field.fieldname, $event.target.value)"
        :placeholder="field.placeholder || ''"
        class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500" />

      <p v-if="field.description && !isCheck(field)" class="text-xs text-gray-500">
        {{ field.description }}
      </p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SchemaFormRenderer',
  props: {
    fields: {
      type: Array,
      default: () => [],
    },
    modelValue: {
      type: Object,
      default: () => ({}),
    },
  },
  emits: ['update:modelValue', 'change'],
  data() {
    return {
      pinflError: '',
    }
  },
  computed: {
    visibleFields() {
      return this.fields.filter((f) => this.evalVisibility(f))
    },
  },
  methods: {
    evalVisibility(field) {
      const cond = field.show_if || field.condition
      if (!cond) return true

      // Simple expression evaluation: "field == 'value'" or "field > 10"
      const match = String(cond).match(/^([a-zA-Z_][a-zA-Z0-9_]*)\s*(==|!=|>=|<=|>|<)\s*(.+)$/)
      if (match) {
        const [, varName, op, rawVal] = match
        const actual = this.modelValue[varName]
        const targetStr = rawVal.trim().replace(/^['"]|['"]$/g, '')

        const numTarget = Number(targetStr)
        const numActual = Number(actual)

        if (!isNaN(numTarget) && !isNaN(numActual)) {
          if (op === '==') return numActual === numTarget
          if (op === '!=') return numActual !== numTarget
          if (op === '>') return numActual > numTarget
          if (op === '<') return numActual < numTarget
          if (op === '>=') return numActual >= numTarget
          if (op === '<=') return numActual <= numTarget
        } else {
          const actStr = String(actual || '').toLowerCase()
          if (op === '==') return actStr === targetStr.toLowerCase()
          if (op === '!=') return actStr !== targetStr.toLowerCase()
        }
      }

      try {
        // Safe evaluation
        const fn = new Function('data', `with(data) { return !!(${cond}); }`)
        return fn(this.modelValue)
      } catch (e) {
        return true
      }
    },
    isSelect(f) {
      const t = String(f.type || f.fieldtype || '').toLowerCase()
      return t === 'select' || Array.isArray(f.options)
    },
    getOptions(f) {
      if (Array.isArray(f.options)) {
        return f.options.map((o) => (typeof o === 'object' ? o : { label: o, value: o }))
      }
      if (typeof f.options === 'string') {
        return f.options
          .split('\n')
          .map((s) => s.trim())
          .filter(Boolean)
          .map((s) => ({ label: s, value: s }))
      }
      return []
    },
    isCheck(f) {
      const t = String(f.type || f.fieldtype || '').toLowerCase()
      return t === 'check' || t === 'boolean'
    },
    isTextarea(f) {
      const t = String(f.type || f.fieldtype || '').toLowerCase()
      return t === 'textarea' || t === 'small text'
    },
    isNumber(f) {
      const t = String(f.type || f.fieldtype || '').toLowerCase()
      return t === 'number' || t === 'currency' || t === 'float' || t === 'int'
    },
    isDate(f) {
      const t = String(f.type || f.fieldtype || '').toLowerCase()
      return t === 'date'
    },
    isPinfl(f) {
      const name = String(f.fieldname || '').toLowerCase()
      const t = String(f.type || f.fieldtype || '').toLowerCase()
      return name.includes('pinfl') || name.includes('jshshir') || t === 'pinfl'
    },
    isPhone(f) {
      const name = String(f.fieldname || '').toLowerCase()
      const t = String(f.type || f.fieldtype || '').toLowerCase()
      return name.includes('phone') || name.includes('mobile') || t === 'phone'
    },
    onPinflInput(fieldname, val) {
      const digits = val.replace(/\D/g, '').slice(0, 14)
      if (digits.length > 0 && digits.length < 14) {
        this.pinflError = `Введено ${digits.length} из 14 цифр`
      } else {
        this.pinflError = ''
      }
      this.updateField(fieldname, digits)
    },
    onPhoneInput(fieldname, val) {
      let digits = val.replace(/\D/g, '')
      if (digits.startsWith('998')) {
        digits = digits.slice(3)
      }
      digits = digits.slice(0, 9)
      const formatted = digits ? `+998${digits}` : ''
      this.updateField(fieldname, formatted)
    },
    updateField(fieldname, val) {
      const updated = { ...this.modelValue, [fieldname]: val }
      this.$emit('update:modelValue', updated)
      this.$emit('change', { fieldname, value: val, data: updated })
    },
  },
}
</script>
