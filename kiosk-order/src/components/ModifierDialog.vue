<template>
  <div class="overlay">
    <div class="dialog">
      <h2>{{ product.name }}</h2>
      <p class="price">{{ unitPrice.toFixed(2) }} €</p>

      <div v-for="group in product.modifiers" :key="group.name" class="group">
        <div class="group-name">
          {{ group.name }}
          <span v-if="group.required" class="required">*povinné</span>
        </div>
        <div class="options">
          <button
            v-for="opt in group.options"
            :key="opt.name"
            :class="['option-btn', { selected: isSelected(group.name, opt.name) }]"
            @click="toggleOption(group, opt)"
          >
            {{ opt.name }}
            <span v-if="parseFloat(opt.price_delta) !== 0" class="delta">
              {{ parseFloat(opt.price_delta) > 0 ? '+' : '' }}{{ parseFloat(opt.price_delta).toFixed(2) }} €
            </span>
          </button>
        </div>
      </div>

      <div class="note-row">
        <label>Opomba za kuhinjo:</label>
        <input v-model="note" type="text" placeholder="npr. brez soli" maxlength="100" />
      </div>

      <div class="total-preview">
        Skupaj: <strong>{{ computedPrice.toFixed(2) }} €</strong>
      </div>

      <div class="actions">
        <button class="cancel" @click="$emit('cancel')">Prekliči</button>
        <button class="confirm" :disabled="!canConfirm" @click="confirm">
          Dodaj v košarico
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Product, ModifierGroup, ModifierOption, SelectedModifier } from '../types'

const props = defineProps<{ product: Product; unitPrice: number }>()
const emit = defineEmits<{
  (e: 'confirm', modifiers: SelectedModifier[], note: string): void
  (e: 'cancel'): void
}>()

const selected = ref<Map<string, string[]>>(new Map())
const note = ref('')

function isSelected(groupName: string, optName: string): boolean {
  return selected.value.get(groupName)?.includes(optName) ?? false
}

function toggleOption(group: ModifierGroup, opt: ModifierOption) {
  const current = selected.value.get(group.name) ?? []
  if (group.multi_select) {
    if (current.includes(opt.name)) {
      selected.value.set(group.name, current.filter(x => x !== opt.name))
    } else {
      selected.value.set(group.name, [...current, opt.name])
    }
  } else {
    selected.value.set(group.name, current[0] === opt.name ? [] : [opt.name])
  }
}

const canConfirm = computed(() =>
  props.product.modifiers
    .filter(g => g.required)
    .every(g => (selected.value.get(g.name)?.length ?? 0) > 0)
)

const computedPrice = computed(() => {
  let extra = 0
  for (const [gName, optNames] of selected.value) {
    const group = props.product.modifiers.find(g => g.name === gName)
    if (!group) continue
    for (const oName of optNames) {
      const opt = group.options.find(o => o.name === oName)
      if (opt) extra += parseFloat(opt.price_delta)
    }
  }
  return props.unitPrice + extra
})

function confirm() {
  const modifiers: SelectedModifier[] = []
  for (const [gName, optNames] of selected.value) {
    const group = props.product.modifiers.find(g => g.name === gName)
    if (!group) continue
    for (const oName of optNames) {
      const opt = group.options.find(o => o.name === oName)
      if (opt) modifiers.push({ group: gName, option: oName, price_delta: parseFloat(opt.price_delta) })
    }
  }
  emit('confirm', modifiers, note.value)
}
</script>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,.6); display: flex; align-items: center; justify-content: center; z-index: 100; overflow-y: auto; padding: 1rem; }
.dialog { background: #fff; border-radius: 12px; padding: 1.5rem; width: 480px; max-height: 90vh; overflow-y: auto; }
h2 { margin: 0 0 0.25rem; }
.price { color: #27ae60; font-size: 1.2rem; margin: 0 0 1.25rem; }
.group { margin-bottom: 1.25rem; }
.group-name { font-weight: 700; margin-bottom: 0.5rem; }
.required { font-size: 0.8rem; color: #c0392b; margin-left: 0.25rem; }
.options { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.option-btn { padding: 0.5rem 1rem; border: 2px solid #ddd; border-radius: 8px; background: #f8f8f8; cursor: pointer; font-size: 0.95rem; }
.option-btn.selected { border-color: #2980b9; background: #ebf5fb; color: #1a6395; font-weight: 700; }
.delta { font-size: 0.8rem; color: #e67e22; margin-left: 0.25rem; }
.note-row { margin: 1rem 0; }
.note-row label { display: block; font-size: 0.9rem; margin-bottom: 0.25rem; color: #555; }
.note-row input { width: 100%; border: 1px solid #ddd; border-radius: 6px; padding: 0.5rem; font-size: 1rem; }
.total-preview { font-size: 1.1rem; margin: 1rem 0; text-align: right; }
.actions { display: flex; gap: 0.75rem; }
button { flex: 1; padding: 0.75rem; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; }
.cancel { background: #ecf0f1; }
.confirm { background: #27ae60; color: #fff; }
.confirm:disabled { background: #bdc3c7; cursor: not-allowed; }
</style>
