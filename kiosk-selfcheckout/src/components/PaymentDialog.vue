<template>
  <div class="overlay">
    <div class="dialog">
      <h2>Plačilo</h2>
      <div class="total-row">
        <span>Skupaj za plačilo:</span>
        <strong>{{ total.toFixed(2) }} €</strong>
      </div>

      <div class="methods">
        <button
          v-for="m in methods"
          :key="m.value"
          :class="['method-btn', { active: selected === m.value }]"
          @click="selected = m.value"
        >
          {{ m.label }}
        </button>
      </div>

      <div v-if="selected === 'cash'" class="cash-section">
        <label>Prejeto gotovino:</label>
        <div class="cash-input-row">
          <input v-model.number="cashGiven" type="number" step="0.01" min="0" ref="cashRef" />
          <span>€</span>
        </div>
        <p v-if="change >= 0" class="change">Vračilo: <strong>{{ change.toFixed(2) }} €</strong></p>
      </div>

      <div v-if="selected === 'sumup'" class="sumup-section">
        <p>Priložite kartico ali telefon bralcu SumUp.</p>
        <p class="sumup-status">{{ sumupStatus }}</p>
      </div>

      <div class="actions">
        <button class="cancel" @click="$emit('cancel')">Prekliči</button>
        <button
          class="confirm"
          :disabled="!canConfirm"
          @click="confirm"
        >
          Plačaj {{ total.toFixed(2) }} €
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import type { PaymentMethod } from '../types'

const props = defineProps<{ total: number }>()
const emit = defineEmits<{
  (e: 'paid', method: PaymentMethod, cashGiven?: number): void
  (e: 'cancel'): void
}>()

const methods = [
  { value: 'cash' as PaymentMethod, label: 'Gotovina' },
  { value: 'card' as PaymentMethod, label: 'Kartica' },
  { value: 'sumup' as PaymentMethod, label: 'SumUp' },
]

const selected = ref<PaymentMethod>('cash')
const cashGiven = ref(0)
const cashRef = ref<HTMLInputElement | null>(null)
const sumupStatus = ref('Čakam na plačilo...')

const change = computed(() => cashGiven.value - props.total)
const canConfirm = computed(() => {
  if (selected.value === 'cash') return cashGiven.value >= props.total
  return true
})

watch(selected, async (m) => {
  if (m === 'cash') {
    await nextTick()
    cashRef.value?.focus()
  }
  if (m === 'sumup') {
    sumupStatus.value = 'Čakam na plačilo...'
    // Real SumUp integration fires a native event; mock auto-approves after 2s
    setTimeout(() => { sumupStatus.value = 'Plačilo odobreno ✓' }, 2000)
  }
})

function confirm() {
  emit('paid', selected.value, selected.value === 'cash' ? cashGiven.value : undefined)
}
</script>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,.55); display: flex; align-items: center; justify-content: center; z-index: 150; }
.dialog { background: #fff; border-radius: 12px; padding: 2rem; width: 440px; }
h2 { margin: 0 0 1rem; text-align: center; }
.total-row { display: flex; justify-content: space-between; align-items: center; font-size: 1.3rem; background: #f8f8f8; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 1.25rem; }
.methods { display: flex; gap: 0.5rem; margin-bottom: 1.25rem; }
.method-btn { flex: 1; padding: 0.7rem; border: 2px solid #ddd; border-radius: 8px; background: #fff; cursor: pointer; font-size: 0.95rem; }
.method-btn.active { border-color: #2980b9; background: #ebf5fb; color: #1a6395; font-weight: 700; }
.cash-section label { font-size: 0.9rem; color: #555; display: block; margin-bottom: 0.4rem; }
.cash-input-row { display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.5rem; }
.cash-input-row input { font-size: 1.5rem; width: 120px; border: 2px solid #ddd; border-radius: 8px; padding: 0.25rem 0.5rem; text-align: right; }
.change { color: #27ae60; font-size: 1.1rem; }
.sumup-section { text-align: center; color: #555; margin-bottom: 0.5rem; }
.sumup-status { font-weight: 700; color: #27ae60; }
.actions { display: flex; gap: 0.75rem; margin-top: 1.25rem; }
button { padding: 0.75rem; flex: 1; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; }
.cancel { background: #ecf0f1; }
.confirm { background: #27ae60; color: #fff; font-size: 1.1rem; }
.confirm:disabled { background: #bdc3c7; cursor: not-allowed; }
</style>
