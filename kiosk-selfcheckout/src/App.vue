<template>
  <div class="kiosk-layout">
    <!-- Header -->
    <header class="kiosk-header">
      <div class="brand">Griltek POS — Samopostrežna blagajna</div>
      <div class="session-info" v-if="phase !== 'idle'">
        {{ cart.lineCount }} art. | {{ cart.total.toFixed(2) }} €
      </div>
    </header>

    <!-- Idle / start screen -->
    <main v-if="phase === 'idle'" class="idle-screen">
      <div class="idle-content">
        <div class="idle-icon">🛒</div>
        <h1>Začnite nakup</h1>
        <p>Skenirajte prvi artikel</p>
        <button class="start-btn" @click="phase = 'scanning'">Začni</button>
      </div>
    </main>

    <!-- Main shopping phase -->
    <main v-else-if="phase === 'scanning'" class="shopping-layout">
      <div class="cart-area">
        <CartTable :lines="cart.lines" @remove="removeLine" />
      </div>
      <div class="sidebar">
        <div class="scan-indicator" :class="{ busy: scanBusy }">
          <span v-if="scanBusy">Iščem artikel...</span>
          <span v-else-if="scanError" class="scan-error">{{ scanError }}</span>
          <span v-else>Skenirajte artikel</span>
        </div>
        <div class="totals">
          <div class="total-line"><span>Vmesna vsota</span><span>{{ cart.subtotal.toFixed(2) }} €</span></div>
          <div class="total-line small"><span>DDV (vključen)</span><span>{{ cart.vatTotal.toFixed(2) }} €</span></div>
          <div class="total-line grand"><span>SKUPAJ</span><span>{{ cart.total.toFixed(2) }} €</span></div>
        </div>
        <div class="sidebar-actions">
          <button class="pay-btn" :disabled="cart.lineCount === 0" @click="phase = 'payment'">
            Plačaj
          </button>
          <button class="cancel-btn" @click="cancelSession">Prekliči nakup</button>
        </div>
      </div>
    </main>

    <!-- Success screen -->
    <main v-else-if="phase === 'success'" class="success-phase">
      <ReceiptScreen :total="lastTotal" :change="lastChange" @done="resetToIdle" />
    </main>

    <!-- Modals -->
    <WeightDialog
      v-if="pendingWeight"
      :product="pendingWeight.product"
      :unit-price="pendingWeight.unitPrice"
      @confirm="onWeightConfirmed"
      @cancel="pendingWeight = null; scanError = 'Tehtanje preklicano.'"
    />

    <AgeCheckDialog
      v-if="pendingAgeCheck"
      :min-age="pendingAgeCheck.minAge"
      @approved="onAgeApproved"
      @denied="onAgeDenied"
    />

    <PaymentDialog
      v-if="phase === 'payment'"
      :total="cart.total"
      @paid="onPaid"
      @cancel="phase = 'scanning'"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import CartTable from './components/CartTable.vue'
import WeightDialog from './components/WeightDialog.vue'
import AgeCheckDialog from './components/AgeCheckDialog.vue'
import PaymentDialog from './components/PaymentDialog.vue'
import ReceiptScreen from './components/ReceiptScreen.vue'
import { createCart } from './stores/cart'
import { useScanner } from './composables/useScanner'
import { checkSecurityScale } from './composables/useSecurityScale'
import { lookupBarcode, fetchPrices, createSale, LOCATION_ID, DEVICE_ID } from './api/client'
import type { Product, Price, PaymentMethod } from './types'

// ── state ────────────────────────────────────────────────────────────────────
type Phase = 'idle' | 'scanning' | 'payment' | 'success'

const phase = ref<Phase>('idle')
const cart = createCart()
const scanBusy = ref(false)
const scanError = ref('')

// pending dialogs
const pendingWeight = ref<{ product: Product; price: Price; unitPrice: number } | null>(null)
const pendingAgeCheck = ref<{ product: Product; price: Price; weight_kg: number | null; minAge: number } | null>(null)

// post-payment
const lastTotal = ref(0)
const lastChange = ref(0)

// audit log (age-check approvals stored locally; in production send to store-server)
const ageAuditLog = reactive<{ ts: string; product_id: string; min_age: number }[]>([])

// ── scanner hook ─────────────────────────────────────────────────────────────
useScanner(async (code) => {
  if (phase.value !== 'scanning') {
    phase.value = 'scanning'
  }
  await handleScan(code)
})

// ── scan logic ────────────────────────────────────────────────────────────────
async function handleScan(code: string) {
  if (scanBusy.value) return
  scanBusy.value = true
  scanError.value = ''
  try {
    const product = await lookupBarcode(code)
    const prices = await fetchPrices(product.id)
    const price = prices.find(p => p.price_type === 'regular') ?? prices[0]
    if (!price) { scanError.value = `Ni cene za ${product.name}`; return }

    if (product.is_weighable) {
      pendingWeight.value = { product, price, unitPrice: parseFloat(price.amount) }
    } else if (product.age_restricted) {
      pendingAgeCheck.value = { product, price, weight_kg: null, minAge: product.min_age ?? 18 }
    } else {
      addToCart(product, price, 1, null, checkProductOnScale(product, 1, null))
    }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    scanError.value = msg.includes('404') ? 'Artikel ni najden.' : 'Napaka pri iskanju.'
  } finally {
    scanBusy.value = false
  }
}

function checkProductOnScale(product: Product, qty: number, weight_kg: number | null): boolean | null {
  // security scale check only when product has weight data and scale tolerance set
  if (!product.weight_grams || !product.weight_tolerance_pct) return null
  if (weight_kg === null) {
    // non-weighable: compare expected weight (weight_grams × qty) vs scale reading
    // In a real deployment, read from scale hardware; here we skip (return null = not checked)
    return null
  }
  // for weighable items the weighed value IS the qty, no security check needed
  return null
}

function onWeightConfirmed(weight_kg: number) {
  if (!pendingWeight.value) return
  const { product, price } = pendingWeight.value
  pendingWeight.value = null
  if (product.age_restricted) {
    pendingAgeCheck.value = { product, price, weight_kg, minAge: product.min_age ?? 18 }
  } else {
    addToCart(product, price, 1, weight_kg, null)
  }
}

function onAgeApproved(_attendantPin: string) {
  if (!pendingAgeCheck.value) return
  const { product, price, weight_kg, minAge } = pendingAgeCheck.value
  ageAuditLog.push({ ts: new Date().toISOString(), product_id: product.id, min_age: minAge })
  pendingAgeCheck.value = null
  addToCart(product, price, 1, weight_kg, checkProductOnScale(product, 1, weight_kg))
}

function onAgeDenied() {
  pendingAgeCheck.value = null
  scanError.value = 'Artikel zavrnjen — starostna omejitev.'
}

function addToCart(product: Product, price: Price, qty: number, weight_kg: number | null, security_scale_ok: boolean | null) {
  cart.add(product, price, qty, weight_kg, security_scale_ok)
}

function removeLine(i: number) {
  cart.removeLine(i)
}

// ── payment ───────────────────────────────────────────────────────────────────
async function onPaid(method: PaymentMethod, cashGiven?: number) {
  const total = cart.total
  const change = method === 'cash' ? (cashGiven ?? 0) - total : 0

  const payload = {
    transaction_uuid: crypto.randomUUID(),
    cash_session_id: null,
    location_id: LOCATION_ID,
    device_id: DEVICE_ID,
    lines: cart.lines.map(l => ({
      product_id: l.product.id,
      product_name: l.product.name,
      plu: l.product.plu,
      qty: l.weight_kg !== null ? l.weight_kg : l.qty,
      unit_price: l.unit_price.toFixed(4),
      vat_rate: l.vat_rate.toFixed(2),
      line_total: l.line_total.toFixed(2),
      vat_amount: l.vat_amount.toFixed(2),
      discount_pct: '0.00',
      discount_amount: '0.00',
    })),
    payments: [{ method, amount: total.toFixed(2) }],
  }

  try {
    await createSale(payload)
  } catch {
    // If offline, sale is lost at kiosk level — in production enqueue to local SQLite
    // For now we still show success to customer; cashier handles reconciliation
  }

  lastTotal.value = total
  lastChange.value = change
  phase.value = 'success'
  cart.clear()
}

function cancelSession() {
  cart.clear()
  phase.value = 'idle'
  scanError.value = ''
}

function resetToIdle() {
  phase.value = 'idle'
}
</script>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: #f0f2f5; color: #222; height: 100vh; overflow: hidden; }
#app { height: 100vh; }
</style>

<style scoped>
.kiosk-layout { display: flex; flex-direction: column; height: 100vh; }
.kiosk-header { background: #2c3e50; color: #fff; display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1.5rem; font-size: 1rem; flex-shrink: 0; }
.brand { font-weight: 700; font-size: 1.1rem; }

/* Idle */
.idle-screen { flex: 1; display: flex; align-items: center; justify-content: center; }
.idle-content { text-align: center; }
.idle-icon { font-size: 5rem; margin-bottom: 1rem; }
h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
p { color: #666; font-size: 1.1rem; margin-bottom: 1.5rem; }
.start-btn { padding: 1rem 3rem; font-size: 1.3rem; background: #27ae60; color: #fff; border: none; border-radius: 12px; cursor: pointer; }

/* Shopping */
.shopping-layout { flex: 1; display: flex; overflow: hidden; }
.cart-area { flex: 1; overflow-y: auto; padding: 1rem; background: #fff; border-right: 1px solid #e0e0e0; }
.sidebar { width: 300px; display: flex; flex-direction: column; padding: 1rem; gap: 1rem; background: #fafafa; }
.scan-indicator { background: #eaf4ff; border: 1px solid #bee3f8; border-radius: 8px; padding: 0.75rem 1rem; text-align: center; font-size: 0.95rem; color: #2980b9; }
.scan-indicator.busy { background: #fffbea; border-color: #f9e07e; color: #856404; }
.scan-error { color: #c0392b; }

.totals { border-top: 1px solid #e0e0e0; padding-top: 0.75rem; }
.total-line { display: flex; justify-content: space-between; padding: 0.3rem 0; font-size: 0.95rem; }
.total-line.small { color: #888; font-size: 0.85rem; }
.total-line.grand { font-size: 1.3rem; font-weight: 700; border-top: 2px solid #333; margin-top: 0.4rem; padding-top: 0.4rem; }

.sidebar-actions { margin-top: auto; display: flex; flex-direction: column; gap: 0.5rem; }
.pay-btn { padding: 1rem; font-size: 1.2rem; background: #27ae60; color: #fff; border: none; border-radius: 10px; cursor: pointer; }
.pay-btn:disabled { background: #bdc3c7; cursor: not-allowed; }
.cancel-btn { padding: 0.65rem; background: #ecf0f1; border: none; border-radius: 8px; cursor: pointer; font-size: 0.9rem; color: #555; }

/* Success */
.success-phase { flex: 1; }
</style>
