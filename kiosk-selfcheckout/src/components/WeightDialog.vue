<template>
  <div class="overlay">
    <div class="dialog">
      <h2>Tehtanje — {{ product.name }}</h2>
      <p class="hint">Položite artikel na tehtnico in potrdite težo.</p>
      <div class="weight-display">
        <input
          v-model.number="weightInput"
          type="number"
          step="0.001"
          min="0"
          placeholder="0.000"
          ref="inputRef"
        />
        <span>kg</span>
      </div>
      <p class="price-preview" v-if="weightInput > 0">
        {{ weightInput.toFixed(3) }} kg × {{ unitPrice.toFixed(2) }} € =
        <strong>{{ (weightInput * unitPrice).toFixed(2) }} €</strong>
      </p>
      <div class="actions">
        <button class="cancel" @click="$emit('cancel')">Prekliči</button>
        <button class="confirm" :disabled="weightInput <= 0" @click="confirm">Potrdi</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { Product } from '../types'

const props = defineProps<{ product: Product; unitPrice: number }>()
const emit = defineEmits<{
  (e: 'confirm', weight_kg: number): void
  (e: 'cancel'): void
}>()

const weightInput = ref(0)
const inputRef = ref<HTMLInputElement | null>(null)

onMounted(() => inputRef.value?.focus())

function confirm() {
  if (weightInput.value > 0) emit('confirm', weightInput.value)
}
</script>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,.5); display: flex; align-items: center; justify-content: center; z-index: 100; }
.dialog { background: #fff; border-radius: 12px; padding: 2rem; width: 420px; text-align: center; }
h2 { margin: 0 0 0.5rem; }
.hint { color: #666; margin: 0 0 1.5rem; }
.weight-display { display: flex; align-items: center; justify-content: center; gap: 0.5rem; margin-bottom: 1rem; }
.weight-display input { font-size: 2rem; width: 160px; text-align: right; border: 2px solid #ddd; border-radius: 8px; padding: 0.25rem 0.5rem; }
.weight-display span { font-size: 1.5rem; color: #555; }
.price-preview { color: #27ae60; font-size: 1.1rem; margin-bottom: 1.5rem; }
.actions { display: flex; gap: 1rem; justify-content: center; }
button { padding: 0.75rem 2rem; border: none; border-radius: 8px; font-size: 1.1rem; cursor: pointer; }
.cancel { background: #ecf0f1; }
.confirm { background: #27ae60; color: #fff; }
.confirm:disabled { background: #bdc3c7; cursor: not-allowed; }
</style>
