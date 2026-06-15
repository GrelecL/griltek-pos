<template>
  <div class="page">
    <div class="detail-header">
      <RouterLink to="/receipts" class="back-btn">‹ Nazaj</RouterLink>
      <span class="header-title">Račun</span>
    </div>

    <div v-if="loading" class="empty">Nalaganje…</div>
    <div v-else-if="!receipt" class="empty">Račun ni bil najden</div>

    <template v-else>
      <!-- summary -->
      <div class="card">
        <div class="summary-date">{{ formatDateFull(receipt.completed_at) }}</div>
        <div class="summary-total">€ {{ receipt.total }}</div>
        <div v-if="parseFloat(receipt.discount_total) > 0" class="summary-row muted">
          <span>Popust</span><span>-€ {{ receipt.discount_total }}</span>
        </div>
        <div class="summary-row muted">
          <span>DDV</span><span>€ {{ receipt.vat_total }}</span>
        </div>
      </div>

      <!-- line items -->
      <div class="card">
        <div class="section-title">Artikli</div>
        <div v-for="(l, i) in receipt.lines" :key="i" class="line-item">
          <div class="line-left">
            <div class="line-name">{{ l.product_name }}</div>
            <div class="line-meta">{{ l.qty }} × €{{ l.unit_price }} · DDV {{ l.vat_rate }}%</div>
          </div>
          <div class="line-total">€ {{ l.line_total }}</div>
        </div>
      </div>

      <!-- payments -->
      <div class="card">
        <div class="section-title">Plačilo</div>
        <div v-for="(p, i) in receipt.payments" :key="i" class="pay-row">
          <span class="pay-method">{{ methodLabel(p.method) }}</span>
          <span class="pay-amount">€ {{ p.amount }}</span>
        </div>
      </div>

      <!-- receipt ID for reference -->
      <div class="receipt-ref">Ref: {{ shortId }}</div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api, type Receipt } from '../api/client'

const route = useRoute()
const receipt = ref<Receipt | null>(null)
const loading = ref(true)

onMounted(async () => {
  try { receipt.value = await api.receipt(route.params.id as string) } catch {}
  finally { loading.value = false }
})

const shortId = computed(() => receipt.value?.id.slice(0, 8) ?? '')

function formatDateFull(iso: string) {
  return new Date(iso).toLocaleString('sl-SI', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

const methodMap: Record<string, string> = {
  cash: 'Gotovina', card: 'Bančna kartica', sumup: 'Kartični terminal',
  gift: 'Darilna kartica', loyalty: 'Točke zvestobe', credit: 'Kredit',
}
function methodLabel(m: string) { return methodMap[m] ?? m }
</script>

<style scoped>
.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 16px 4px;
}
.back-btn { color: var(--brand); font-size: 17px; font-weight: 600; }
.header-title { font-size: 17px; font-weight: 700; }

.summary-date { font-size: 13px; color: var(--muted); margin-bottom: 6px; text-transform: capitalize; }
.summary-total { font-size: 40px; font-weight: 800; margin-bottom: 8px; }
.summary-row { display: flex; justify-content: space-between; font-size: 14px; }
.muted { color: var(--muted); }

.section-title { font-size: 13px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.5px; color: var(--muted); margin-bottom: 12px; }

.line-item { display: flex; justify-content: space-between; align-items: flex-start; padding: 10px 0; }
.line-item + .line-item { border-top: 1px solid var(--border); }
.line-left { flex: 1; }
.line-name { font-size: 15px; font-weight: 500; }
.line-meta { font-size: 12px; color: var(--muted); margin-top: 2px; }
.line-total { font-size: 15px; font-weight: 700; }

.pay-row { display: flex; justify-content: space-between; padding: 8px 0; }
.pay-row + .pay-row { border-top: 1px solid var(--border); }
.pay-method { font-size: 15px; }
.pay-amount { font-size: 15px; font-weight: 700; }

.receipt-ref {
  text-align: center;
  font-size: 11px;
  color: var(--muted);
  font-family: monospace;
  padding: 8px 0 24px;
}
</style>
