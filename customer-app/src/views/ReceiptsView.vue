<template>
  <div class="page">
    <div class="page-title">Moji računi</div>
    <div class="page-sub">Zgodovina nakupov</div>

    <div v-if="loading" class="empty">Nalaganje…</div>
    <div v-else-if="!receipts.length" class="empty">
      <div style="font-size:40px;margin-bottom:12px">🧾</div>
      Še nimate shranjenih računov
    </div>

    <div v-else class="receipts-list">
      <RouterLink
        v-for="r in receipts"
        :key="r.id"
        :to="`/receipts/${r.id}`"
        class="receipt-row"
      >
        <div class="receipt-left">
          <div class="receipt-date">{{ formatDate(r.completed_at) }}</div>
          <div class="receipt-time">{{ formatTime(r.completed_at) }}</div>
        </div>
        <div class="receipt-right">
          <div class="receipt-total">€ {{ r.total }}</div>
          <div class="receipt-items">{{ r.lines.length }} {{ r.lines.length === 1 ? 'artikel' : 'artiklov' }}</div>
        </div>
        <div class="receipt-arrow">›</div>
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { api, type Receipt } from '../api/client'

const receipts = ref<Receipt[]>([])
const loading = ref(true)

onMounted(async () => {
  try { receipts.value = await api.receipts() } catch {}
  finally { loading.value = false }
})

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('sl-SI', { day: 'numeric', month: 'short', year: 'numeric' })
}
function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString('sl-SI', { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.receipts-list { padding: 0 16px; display: flex; flex-direction: column; gap: 2px; }

.receipt-row {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--surface);
  padding: 16px;
  border-radius: 14px;
  border: 1px solid var(--border);
}
.receipt-row:first-child { border-radius: 14px 14px 6px 6px; }
.receipt-row:last-child { border-radius: 6px 6px 14px 14px; }
.receipt-row:only-child { border-radius: 14px; }

.receipt-left { flex: 1; }
.receipt-date { font-size: 15px; font-weight: 600; }
.receipt-time { font-size: 12px; color: var(--muted); }

.receipt-right { text-align: right; }
.receipt-total { font-size: 17px; font-weight: 700; }
.receipt-items { font-size: 12px; color: var(--muted); }

.receipt-arrow { color: var(--muted); font-size: 20px; margin-left: 4px; }
</style>
