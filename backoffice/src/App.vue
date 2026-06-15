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

      <!-- Customers -->
      <div v-else-if="page === 'customers'" class="page">
        <h1>Stranke</h1>
        <div v-if="!TENANT_ID" class="notice">Nastavite VITE_TENANT_ID v okolišu.</div>
        <div v-else-if="customersLoading" class="loading-full">Nalagam...</div>
        <template v-else>
          <DataTable
            title="Stranke"
            :columns="customerCols"
            :rows="customers"
            :loading="customersLoading"
          />
        </template>
        <button class="refresh-btn" @click="loadCustomers">Osveži</button>
      </div>

      <!-- Coupons -->
      <div v-else-if="page === 'coupons'" class="page">
        <div class="page-header">
          <h1>Kuponi</h1>
          <button class="btn-primary" @click="showCouponForm = !showCouponForm">
            {{ showCouponForm ? 'Zapri' : '+ Nov kupon' }}
          </button>
        </div>

        <div v-if="showCouponForm" class="form-card">
          <h2>Nov kupon</h2>
          <div class="form-grid">
            <div class="field">
              <label>Koda</label>
              <input v-model="newCoupon.code" type="text" placeholder="SAVE10" />
            </div>
            <div class="field">
              <label>Naziv</label>
              <input v-model="newCoupon.name" type="text" placeholder="10% popust" />
            </div>
            <div class="field">
              <label>Tip popusta</label>
              <select v-model="newCoupon.discount_type">
                <option value="pct_discount">Odstotek (%)</option>
                <option value="fixed_discount">Fiksni znesek (€)</option>
              </select>
            </div>
            <div class="field">
              <label>Vrednost</label>
              <input v-model="newCoupon.discount_value" type="number" min="0" step="0.01" />
            </div>
            <div class="field">
              <label>Veljavno od</label>
              <input v-model="newCoupon.valid_from" type="datetime-local" />
            </div>
            <div class="field">
              <label>Veljavno do</label>
              <input v-model="newCoupon.valid_until" type="datetime-local" />
            </div>
            <div class="field">
              <label>Maks. uporab</label>
              <input v-model="newCoupon.max_uses" type="number" min="1" placeholder="neomejeno" />
            </div>
            <div class="field">
              <label>Limit/stranka</label>
              <input v-model="newCoupon.per_customer_limit" type="number" min="1" value="1" />
            </div>
          </div>
          <p v-if="couponError" class="error-msg">{{ couponError }}</p>
          <button class="btn-primary" :disabled="couponSaving" @click="saveCoupon">
            {{ couponSaving ? 'Shranjevanje...' : 'Shrani kupon' }}
          </button>
        </div>

        <div v-if="couponsLoading" class="loading-full">Nalagam...</div>
        <DataTable v-else title="Kuponi" :columns="couponCols" :rows="coupons" :loading="couponsLoading" />
        <button class="refresh-btn" @click="loadCoupons">Osveži</button>
      </div>

      <!-- Registration QR -->
      <div v-else-if="page === 'regqr'" class="page">
        <h1>QR za registracijo</h1>
        <div v-if="!TENANT_SLUG" class="notice">Nastavite VITE_TENANT_SLUG v okolišu.</div>
        <template v-else>
          <p class="reg-hint">Pokažite to QR kodo stranki — aplikacija se odpre s predizpolnjenim poljem za naziv trgovine.</p>
          <div class="qr-wrapper">
            <canvas ref="qrCanvas" class="qr-canvas"></canvas>
          </div>
          <p class="qr-url">{{ registrationUrl }}</p>
        </template>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import QRCode from 'qrcode'
import StatCard from './components/StatCard.vue'
import DataTable from './components/DataTable.vue'
import {
  fetchDashboard, fetchSalesByProduct, fetchPaymentBreakdown, fetchVATBreakdown,
  fetchSyncHealth, fetchCustomers, fetchCoupons, createCoupon, csvUrl, CUSTOMER_APP_URL,
  type DashboardData, type ProductRow, type PaymentRow, type VATRow, type SyncHealth,
  type CustomerRow, type CouponRow, type CouponCreate,
} from './api/client'

const LOCATION_ID = (import.meta.env.VITE_LOCATION_ID as string) || ''
const WAREHOUSE_ID = (import.meta.env.VITE_WAREHOUSE_ID as string) || ''
const TENANT_ID = (import.meta.env.VITE_TENANT_ID as string) || ''
const TENANT_SLUG = (import.meta.env.VITE_TENANT_SLUG as string) || ''

type Page = 'dashboard' | 'reports' | 'sync' | 'customers' | 'coupons' | 'regqr'
const page = ref<Page>('dashboard')
const nav = [
  { id: 'dashboard' as Page, label: 'Nadzorna plošča' },
  { id: 'reports' as Page, label: 'Poročila' },
  { id: 'sync' as Page, label: 'Sinhronizacija' },
  { id: 'customers' as Page, label: 'Stranke' },
  { id: 'coupons' as Page, label: 'Kuponi' },
  { id: 'regqr' as Page, label: 'Reg. QR' },
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

// ── Customers ─────────────────────────────────────────────────────────────────

const customers = ref<CustomerRow[]>([])
const customersLoading = ref(false)
const customerCols = [
  { key: 'name', label: 'Ime' },
  { key: 'phone', label: 'Telefon' },
  { key: 'email', label: 'E-mail' },
]

async function loadCustomers() {
  if (!TENANT_ID) return
  customersLoading.value = true
  try { customers.value = await fetchCustomers(TENANT_ID) }
  catch { customers.value = [] }
  finally { customersLoading.value = false }
}

// ── Coupons ───────────────────────────────────────────────────────────────────

const coupons = ref<CouponRow[]>([])
const couponsLoading = ref(false)
const showCouponForm = ref(false)
const couponSaving = ref(false)
const couponError = ref('')
const couponCols = [
  { key: 'code', label: 'Koda' },
  { key: 'name', label: 'Naziv' },
  { key: 'discount_type', label: 'Tip' },
  { key: 'discount_value', label: 'Vrednost' },
  { key: 'used_count', label: 'Uporab' },
  { key: 'is_active', label: 'Aktiven' },
]

const newCoupon = ref<CouponCreate & { valid_from: string; valid_until: string; max_uses: string; per_customer_limit: number }>({
  code: '', name: '', discount_type: 'pct_discount', discount_value: 0,
  valid_from: '', valid_until: '', max_uses: '', per_customer_limit: 1,
})

async function loadCoupons() {
  couponsLoading.value = true
  try { coupons.value = await fetchCoupons() }
  catch { coupons.value = [] }
  finally { couponsLoading.value = false }
}

async function saveCoupon() {
  couponError.value = ''
  couponSaving.value = true
  try {
    const payload: CouponCreate = {
      tenant_id: TENANT_ID || undefined,
      code: newCoupon.value.code,
      name: newCoupon.value.name,
      discount_type: newCoupon.value.discount_type,
      discount_value: newCoupon.value.discount_value,
      per_customer_limit: newCoupon.value.per_customer_limit,
    }
    if (newCoupon.value.valid_from) payload.valid_from = new Date(newCoupon.value.valid_from).toISOString()
    if (newCoupon.value.valid_until) payload.valid_until = new Date(newCoupon.value.valid_until).toISOString()
    if (newCoupon.value.max_uses) payload.max_uses = parseInt(newCoupon.value.max_uses as string)
    await createCoupon(payload)
    showCouponForm.value = false
    newCoupon.value = { code: '', name: '', discount_type: 'pct_discount', discount_value: 0, valid_from: '', valid_until: '', max_uses: '', per_customer_limit: 1 }
    await loadCoupons()
  } catch (e: any) {
    couponError.value = e.message ?? 'Napaka pri shranjevanju'
  } finally {
    couponSaving.value = false
  }
}

// ── Registration QR ───────────────────────────────────────────────────────────

const qrCanvas = ref<HTMLCanvasElement | null>(null)
const registrationUrl = computed(() => TENANT_SLUG ? `${CUSTOMER_APP_URL}/login?tenant=${TENANT_SLUG}` : '')

watch([page, qrCanvas], async ([p]) => {
  if (p === 'regqr' && TENANT_SLUG) {
    await nextTick()
    if (qrCanvas.value) {
      await QRCode.toCanvas(qrCanvas.value, registrationUrl.value, { width: 280, margin: 2 })
    }
  }
})

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

/* Customers / Coupons */
.notice { background: #fdebd0; border-radius: 8px; padding: 1rem; color: #935116; margin-bottom: 1rem; }

/* Coupon form */
.form-card { background: #fff; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.form-card h2 { font-size: 1.1rem; margin-bottom: 1rem; }
.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1rem; }
.field { display: flex; flex-direction: column; gap: 4px; }
.field label { font-size: 0.8rem; font-weight: 600; color: #666; }
.field input, .field select { border: 1px solid #ddd; border-radius: 6px; padding: 0.4rem 0.6rem; font-size: 0.9rem; }
.btn-primary { padding: 0.55rem 1.25rem; background: #2980b9; color: #fff; border: none; border-radius: 8px; cursor: pointer; font-size: 0.9rem; font-weight: 600; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.error-msg { color: #c0392b; font-size: 0.875rem; margin-bottom: 0.75rem; }

/* Registration QR */
.reg-hint { color: #555; margin-bottom: 1.5rem; }
.qr-wrapper { background: #fff; display: inline-flex; border-radius: 12px; padding: 1.25rem; box-shadow: 0 1px 8px rgba(0,0,0,.12); margin-bottom: 1rem; }
.qr-canvas { display: block; }
.qr-url { font-size: 0.85rem; color: #777; word-break: break-all; max-width: 320px; }
</style>
