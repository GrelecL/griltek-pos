<template>
  <div class="bo-layout">
    <nav class="sidebar">
      <div class="logo">Griltek POS</div>
      <button
        v-for="item in nav"
        :key="item.id"
        :class="['nav-btn', { active: page === item.id }]"
        @click="page = item.id"
      >{{ item.label }}</button>
    </nav>

    <main class="content">
      <!-- Dashboard -->
      <div v-if="page === 'dashboard'" class="page">
        <div class="page-header">
          <h1>Nadzorna plošča</h1>
          <div class="date-range">
            <input type="date" v-model="dateFrom" @change="loadDashboard" />
            <span>—</span>
            <input type="date" v-model="dateTo" @change="loadDashboard" />
          </div>
        </div>

        <div v-if="dashLoading" class="loading-full">Nalagam...</div>
        <template v-else-if="dash">
          <div class="stats-grid">
            <StatCard label="Prodaje" :value="dash.sales.count" />
            <StatCard label="Prihodek" :value="`${parseFloat(dash.sales.revenue).toFixed(2)} €`" />
            <StatCard label="Vračila" :value="dash.returns.count" :sub="`${parseFloat(dash.returns.total).toFixed(2)} €`" />
            <StatCard label="Neto prihodek" :value="`${parseFloat(dash.net_revenue).toFixed(2)} €`" />
            <StatCard
              label="Čakajoče fiskalizacije"
              :value="dash.pending_fiscal"
              :sub="dash.pending_fiscal > 0 ? 'Zahteva pozornost' : 'OK'"
            />
          </div>

          <div class="charts-row">
            <DataTable
              title="Prodaje po artiklih"
              :columns="productCols"
              :rows="productRows"
              :loading="productLoading"
              :download-url="productCsvUrl"
            />
            <DataTable
              title="Načini plačila"
              :columns="paymentCols"
              :rows="paymentRows"
              :loading="paymentLoading"
            />
          </div>

          <DataTable
            title="DDV razčlenitev"
            :columns="vatCols"
            :rows="vatRows"
            :loading="vatLoading"
          />
        </template>
      </div>

      <!-- Reports -->
      <div v-else-if="page === 'reports'" class="page">
        <h1>Poročila</h1>
        <div class="report-cards">
          <div class="report-card" @click="downloadReport('sales')">
            <div class="rc-icon">📊</div>
            <div>Prodaje (CSV)</div>
          </div>
          <div class="report-card" @click="downloadReport('by-product')">
            <div class="rc-icon">📦</div>
            <div>Po artiklih (CSV)</div>
          </div>
          <div class="report-card" @click="downloadReport('stock')">
            <div class="rc-icon">🏭</div>
            <div>Zalogo (CSV)</div>
          </div>
          <div class="report-card" @click="downloadReport('fiscal')">
            <div class="rc-icon">🧾</div>
            <div>Fiskalizacija (JSON)</div>
          </div>
        </div>
        <p class="report-hint">Kliknite na poročilo za prenos. Datum-filter velja iz nadzorne plošče.</p>
      </div>

      <!-- Sync health -->
      <div v-else-if="page === 'sync'" class="page">
        <h1>Zdravje sinhronizacije</h1>
        <div v-if="syncLoading" class="loading-full">Nalagam...</div>
        <template v-else-if="syncHealth">
          <div :class="['sync-status', syncHealth.status === 'ok' ? 'ok' : 'degraded']">
            {{ syncHealth.status === 'ok' ? '● Vse sinhronizovano' : '⚠ Zaostanki zaznani' }}
          </div>
          <div class="stats-grid">
            <StatCard label="Čakajoče fiskalizacije" :value="syncHealth.pending_fiscal_records" />
            <StatCard label="Nesinhron. premiki zalog" :value="syncHealth.unsynced_stock_movements" />
          </div>
        </template>
        <button class="refresh-btn" @click="loadSync">Osveži</button>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import StatCard from './components/StatCard.vue'
import DataTable from './components/DataTable.vue'
import {
  fetchDashboard, fetchSalesByProduct, fetchPaymentBreakdown, fetchVATBreakdown,
  fetchSyncHealth, csvUrl,
  type DashboardData, type ProductRow, type PaymentRow, type VATRow, type SyncHealth,
} from './api/client'

const LOCATION_ID = (import.meta.env.VITE_LOCATION_ID as string) || ''
const WAREHOUSE_ID = (import.meta.env.VITE_WAREHOUSE_ID as string) || ''

type Page = 'dashboard' | 'reports' | 'sync'
const page = ref<Page>('dashboard')
const nav = [
  { id: 'dashboard' as Page, label: 'Nadzorna plošča' },
  { id: 'reports' as Page, label: 'Poročila' },
  { id: 'sync' as Page, label: 'Sinhronizacija' },
]

// date range
const today = new Date().toISOString().slice(0, 10)
const firstOfMonth = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().slice(0, 10)
const dateFrom = ref(firstOfMonth)
const dateTo = ref(today)

// dashboard
const dash = ref<DashboardData | null>(null)
const dashLoading = ref(false)
const productRows = ref<ProductRow[]>([])
const productLoading = ref(false)
const paymentRows = ref<PaymentRow[]>([])
const paymentLoading = ref(false)
const vatRows = ref<VATRow[]>([])
const vatLoading = ref(false)

const productCols = [
  { key: 'plu', label: 'PLU' },
  { key: 'product_name', label: 'Artikel' },
  { key: 'total_qty', label: 'Kol.' },
  { key: 'total_revenue', label: 'Prihodek (€)' },
  { key: 'total_vat', label: 'DDV (€)' },
]
const paymentCols = [
  { key: 'method', label: 'Način' },
  { key: 'count', label: 'Št.' },
  { key: 'total', label: 'Skupaj (€)' },
]
const vatCols = [
  { key: 'vat_rate', label: 'Stopnja (%)' },
  { key: 'taxable', label: 'Osnova (€)' },
  { key: 'vat', label: 'DDV (€)' },
]

const productCsvUrl = computed(() =>
  csvUrl('/api/v1/reports/sales/by-product', { location_id: LOCATION_ID, date_from: dateFrom.value, date_to: dateTo.value })
)

async function loadDashboard() {
  if (!LOCATION_ID) return
  dashLoading.value = true
  productLoading.value = true
  paymentLoading.value = true
  vatLoading.value = true
  try {
    const [d, p, pay, vat] = await Promise.all([
      fetchDashboard(LOCATION_ID, dateFrom.value, dateTo.value),
      fetchSalesByProduct(LOCATION_ID, dateFrom.value, dateTo.value),
      fetchPaymentBreakdown(LOCATION_ID, dateFrom.value, dateTo.value),
      fetchVATBreakdown(LOCATION_ID, dateFrom.value, dateTo.value),
    ])
    dash.value = d
    productRows.value = p as unknown as ProductRow[]
    paymentRows.value = pay as unknown as PaymentRow[]
    vatRows.value = vat as unknown as VATRow[]
  } catch {
    // offline — show empty
  } finally {
    dashLoading.value = false
    productLoading.value = false
    paymentLoading.value = false
    vatLoading.value = false
  }
}

// sync health
const syncHealth = ref<SyncHealth | null>(null)
const syncLoading = ref(false)

async function loadSync() {
  syncLoading.value = true
  try {
    syncHealth.value = await fetchSyncHealth()
  } catch {
    syncHealth.value = null
  } finally {
    syncLoading.value = false
  }
}

function downloadReport(type: string) {
  const urls: Record<string, string> = {
    'sales': csvUrl('/api/v1/reports/sales', { location_id: LOCATION_ID, date_from: dateFrom.value, date_to: dateTo.value }),
    'by-product': csvUrl('/api/v1/reports/sales/by-product', { location_id: LOCATION_ID, date_from: dateFrom.value, date_to: dateTo.value }),
    'stock': csvUrl('/api/v1/reports/stock', { warehouse_id: WAREHOUSE_ID }),
    'fiscal': `/api/v1/reports/fiscal?date_from=${dateFrom.value}&date_to=${dateTo.value}`,
  }
  window.open(urls[type], '_blank')
}

onMounted(() => { loadDashboard(); loadSync() })
</script>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: #f0f2f5; color: #222; }
#app { min-height: 100vh; }
</style>

<style scoped>
.bo-layout { display: flex; min-height: 100vh; }
.sidebar { width: 200px; background: #1a2a3a; color: #fff; display: flex; flex-direction: column; padding: 1.5rem 0; flex-shrink: 0; }
.logo { font-size: 1rem; font-weight: 700; padding: 0 1.25rem 1.5rem; color: #7fb3d3; }
.nav-btn { display: block; width: 100%; padding: 0.75rem 1.25rem; text-align: left; border: none; background: transparent; color: #ccc; cursor: pointer; font-size: 0.95rem; }
.nav-btn:hover { background: #243447; color: #fff; }
.nav-btn.active { background: #2980b9; color: #fff; }

.content { flex: 1; padding: 2rem; overflow-y: auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
h1 { font-size: 1.5rem; margin-bottom: 1.5rem; }
.page-header h1 { margin: 0; }
.date-range { display: flex; align-items: center; gap: 0.5rem; }
.date-range input { border: 1px solid #ddd; border-radius: 6px; padding: 0.4rem 0.6rem; font-size: 0.9rem; }
.loading-full { padding: 3rem; text-align: center; color: #aaa; }

.stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
.charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }

/* Reports */
.report-cards { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem; }
.report-card { background: #fff; border-radius: 10px; padding: 1.5rem; width: 160px; text-align: center; cursor: pointer; box-shadow: 0 1px 4px rgba(0,0,0,.08); font-size: 0.9rem; }
.report-card:hover { background: #ebf5fb; }
.rc-icon { font-size: 2rem; margin-bottom: 0.5rem; }
.report-hint { color: #aaa; font-size: 0.85rem; }

/* Sync health */
.sync-status { font-size: 1.1rem; font-weight: 700; padding: 0.75rem 1.25rem; border-radius: 8px; margin-bottom: 1.5rem; display: inline-block; }
.sync-status.ok { background: #d5f5e3; color: #1e8449; }
.sync-status.degraded { background: #fdebd0; color: #935116; }
.refresh-btn { margin-top: 1.5rem; padding: 0.6rem 1.5rem; background: #2980b9; color: #fff; border: none; border-radius: 8px; cursor: pointer; font-size: 0.95rem; }
</style>
