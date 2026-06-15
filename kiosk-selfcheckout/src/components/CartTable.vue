<template>
  <div class="cart-table">
    <div v-if="lines.length === 0" class="empty">
      <p>Skenirajte artikel za začetek nakupa</p>
    </div>
    <table v-else>
      <thead>
        <tr>
          <th>Artikel</th>
          <th>Cena/enota</th>
          <th>Kol.</th>
          <th>Skupaj</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(line, i) in lines" :key="i" :class="{ flagged: line.security_scale_ok === false }">
          <td>
            <span class="name">{{ line.product.name }}</span>
            <span v-if="line.product.allergens?.length" class="allergens">
              {{ line.product.allergens.join(', ') }}
            </span>
            <span v-if="line.security_scale_ok === false" class="flag">⚠ Tehtnica</span>
          </td>
          <td>{{ fmt(line.unit_price) }} €<span v-if="line.product.is_weighable">/kg</span></td>
          <td>
            <span v-if="line.weight_kg !== null">{{ line.weight_kg.toFixed(3) }} kg</span>
            <span v-else>{{ line.qty }}</span>
          </td>
          <td>{{ fmt(line.line_total) }} €</td>
          <td>
            <button class="remove" @click="$emit('remove', i)">✕</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import type { CartLine } from '../types'

defineProps<{ lines: CartLine[] }>()
defineEmits<{ (e: 'remove', i: number): void }>()

function fmt(v: number): string {
  return v.toFixed(2)
}
</script>

<style scoped>
.cart-table { flex: 1; overflow-y: auto; }
.empty { display: flex; align-items: center; justify-content: center; height: 100%; color: #888; font-size: 1.2rem; }
table { width: 100%; border-collapse: collapse; }
th { background: #f5f5f5; padding: 0.5rem 0.75rem; text-align: left; font-size: 0.85rem; color: #555; }
td { padding: 0.6rem 0.75rem; border-bottom: 1px solid #eee; vertical-align: top; }
.name { display: block; font-weight: 600; }
.allergens { display: block; font-size: 0.75rem; color: #e67e22; }
.flag { display: block; font-size: 0.75rem; color: #c0392b; font-weight: 700; }
tr.flagged td { background: #fff5f5; }
.remove { background: none; border: none; font-size: 1.1rem; cursor: pointer; color: #c0392b; padding: 0 0.25rem; }
</style>
