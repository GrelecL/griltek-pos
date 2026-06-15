<template>
  <div class="layout">
    <header>
      <span class="brand">Griltek POS — Naročilo</span>
      <div class="service-toggle">
        <button :class="{ active: cart.serviceType === 'eat_in' }" @click="cart.serviceType = 'eat_in'">
          🍽️ Za tukaj
        </button>
        <button :class="{ active: cart.serviceType === 'take_away' }" @click="cart.serviceType = 'take_away'">
          🥡 Za odnesti
        </button>
      </div>
    </header>

    <!-- Menu browser -->
    <div v-if="phase === 'menu'" class="main">
      <aside class="categories">
        <button
          v-for="cat in categories"
          :key="cat.id"
          :class="['cat-btn', { active: selectedCat === cat.id }]"
          @click="selectCategory(cat.id)"
        >{{ cat.name }}</button>
      </aside>
      <section class="products">
        <div v-if="loading" class="loading">Nalagam...</div>
        <div v-else class="product-grid">
          <button
            v-for="p in products"
            :key="p.id"
            class="product-tile"
            @click="selectProduct(p)"
          >
            <div class="tile-name">{{ p.name }}</div>
            <div class="tile-price">{{ priceMap[p.id] ?? '...' }} €</div>
            <div v-if="p.allergens?.length" class="tile-allergens">{{ p.allergens.join(', ') }}</div>
          </button>
        </div>
      </section>
      <div class="cart-panel">
        <div class="cart-lines">
          <div v-if="cart.lineCount === 0" class="cart-empty">Košarica je prazna</div>
          <div v-for="(line, i) in cart.lines" :key="i" class="cart-line">
            <span class="line-name">{{ line.qty }}× {{ line.product.name }}</span>
            <span v-if="line.modifiers.length" class="line-mods">
              {{ line.modifiers.map(m => m.option).join(', ') }}
            </span>
            <span class="line-total">{{ line.line_total.toFixed(2) }} €</span>
            <button class="line-remove" @click="cart.removeLine(i)">✕</button>
          </div>
        </div>
        <div class="cart-footer">
          <div class="cart-total">Skupaj: <strong>{{ cart.total.toFixed(2) }} €</strong></div>
          <button class="order-btn" :disabled="cart.lineCount === 0" @click="phase = 'confirm'">
            Naroči
          </button>
        </div>
      </div>
    </div>

    <!-- Confirm / pager -->
    <div v-else-if="phase === 'confirm'" class="confirm-phase">
      <h2>Potrditev naročila</h2>
      <div class="summary">
        <div v-for="(line, i) in cart.lines" :key="i" class="sum-line">
          <span>{{ line.qty }}× {{ line.product.name }}</span>
          <span>{{ line.line_total.toFixed(2) }} €</span>
        </div>
        <div class="sum-total">
          <span>SKUPAJ</span><span>{{ cart.total.toFixed(2) }} €</span>
        </div>
      </div>
      <div class="pager-row">
        <label>Številka pagerja (neobvezno):</label>
        <input v-model="pagerInput" type="text" maxlength="10" placeholder="npr. 42" />
      </div>
      <div class="confirm-actions">
        <button class="back-btn" @click="phase = 'menu'">Nazaj</button>
        <button class="submit-btn" :disabled="submitting" @click="submitOrder">
          {{ submitting ? 'Pošiljam...' : 'Potrdi naročilo' }}
        </button>
      </div>
    </div>

    <!-- Success -->
    <div v-else-if="phase === 'success'" class="success-phase">
      <div class="success-icon">✓</div>
      <h1>Naročilo sprejeto!</h1>
      <p v-if="pagerInput">Vaša številka pagerja: <strong>{{ pagerInput }}</strong></p>
      <p>Poberite hrano pri pultu.</p>
      <div class="countdown">Nova seja čez {{ countdown }}s</div>
    </div>

    <!-- Modifier dialog -->
    <ModifierDialog
      v-if="pendingProduct"
      :product="pendingProduct"
      :unit-price="pendingPrice"
      @confirm="onModifierConfirm"
      @cancel="pendingProduct = null"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import ModifierDialog from './components/ModifierDialog.vue'
import { createOrderCart } from './stores/orderCart'
import { fetchCategories, fetchProducts, fetchPrice, submitOrder as apiSubmitOrder, LOCATION_ID } from './api/client'
import type { Category, Product, SelectedModifier } from './types'

type Phase = 'menu' | 'confirm' | 'success'

const phase = ref<Phase>('menu')
const cart = createOrderCart()
const categories = ref<Category[]>([])
const products = ref<Product[]>([])
const priceMap = ref<Record<string, string>>({})
const selectedCat = ref<string | null>(null)
const loading = ref(false)

const pendingProduct = ref<Product | null>(null)
const pendingPrice = ref(0)

const pagerInput = ref('')
const submitting = ref(false)
const countdown = ref(8)

const DUMMY_USER = '00000000-0000-0000-0000-000000000001'

onMounted(async () => {
  try {
    categories.value = await fetchCategories()
    if (categories.value.length) await selectCategory(categories.value[0].id)
  } catch {
    // store-server offline: show empty menu
  }
})

async function selectCategory(catId: string) {
  selectedCat.value = catId
  loading.value = true
  try {
    products.value = (await fetchProducts(catId)).filter(p => p.is_active)
    await Promise.all(products.value.slice(0, 20).map(async p => {
      const pr = await fetchPrice(p.id)
      if (pr) priceMap.value[p.id] = parseFloat(pr.amount).toFixed(2)
    }))
  } finally {
    loading.value = false
  }
}

async function selectProduct(p: Product) {
  const pr = await fetchPrice(p.id)
  pendingPrice.value = parseFloat(pr?.amount ?? '0')
  if (p.modifiers?.length) {
    pendingProduct.value = p
  } else {
    cart.add(p, pendingPrice.value, [], null)
  }
}

function onModifierConfirm(modifiers: SelectedModifier[], _note: string) {
  if (!pendingProduct.value) return
  cart.add(pendingProduct.value, pendingPrice.value, modifiers, null)
  pendingProduct.value = null
}

async function submitOrder() {
  submitting.value = true
  try {
    await apiSubmitOrder({
      location_id: LOCATION_ID,
      user_id: DUMMY_USER,
      service_type: cart.serviceType,
      pager_number: pagerInput.value || null,
      lines: cart.lines.map(l => ({
        product_id: l.product.id,
        product_name: l.product.name,
        plu: l.product.plu,
        qty: l.qty,
        unit_price: l.unit_price.toFixed(4),
        vat_rate: l.product.vat_rate,
        course: l.course,
        modifiers: l.modifiers,
      })),
    })
    phase.value = 'success'
    cart.clear()
    startCountdown()
  } catch {
    alert('Napaka pri oddaji naročila. Poskusite znova.')
  } finally {
    submitting.value = false
  }
}

function startCountdown() {
  countdown.value = 8
  const t = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(t)
      phase.value = 'menu'
      pagerInput.value = ''
    }
  }, 1000)
}
</script>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: #f5f5f5; height: 100vh; overflow: hidden; }
#app { height: 100vh; }
</style>

<style scoped>
.layout { display: flex; flex-direction: column; height: 100vh; }
header { background: #2c3e50; color: #fff; display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1.5rem; flex-shrink: 0; }
.brand { font-weight: 700; }
.service-toggle { display: flex; gap: 0.5rem; }
.service-toggle button { padding: 0.4rem 1rem; border: 2px solid #fff3; border-radius: 20px; background: transparent; color: #fff; cursor: pointer; font-size: 0.9rem; }
.service-toggle button.active { background: #27ae60; border-color: #27ae60; }

.main { flex: 1; display: flex; overflow: hidden; }
.categories { width: 160px; background: #fff; border-right: 1px solid #e0e0e0; overflow-y: auto; padding: 0.5rem; flex-shrink: 0; }
.cat-btn { display: block; width: 100%; padding: 0.75rem 0.5rem; text-align: left; border: none; border-radius: 8px; background: transparent; cursor: pointer; margin-bottom: 0.25rem; font-size: 0.95rem; }
.cat-btn.active { background: #ebf5fb; color: #1a6395; font-weight: 700; }
.products { flex: 1; overflow-y: auto; padding: 1rem; }
.loading { padding: 2rem; text-align: center; color: #888; }
.product-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 0.75rem; }
.product-tile { padding: 1rem; background: #fff; border: 2px solid #e0e0e0; border-radius: 10px; cursor: pointer; text-align: left; }
.product-tile:hover { border-color: #2980b9; }
.tile-name { font-weight: 700; margin-bottom: 0.4rem; font-size: 0.95rem; }
.tile-price { color: #27ae60; font-size: 1.1rem; font-weight: 700; }
.tile-allergens { font-size: 0.7rem; color: #e67e22; margin-top: 0.25rem; }

.cart-panel { width: 280px; background: #fff; border-left: 1px solid #e0e0e0; display: flex; flex-direction: column; }
.cart-lines { flex: 1; overflow-y: auto; padding: 0.75rem; }
.cart-empty { color: #aaa; text-align: center; padding: 2rem 0; font-size: 0.9rem; }
.cart-line { display: flex; flex-wrap: wrap; gap: 0.25rem; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid #f0f0f0; font-size: 0.9rem; }
.line-name { flex: 1; }
.line-mods { width: 100%; font-size: 0.75rem; color: #888; padding-left: 0.5rem; }
.line-total { font-weight: 700; }
.line-remove { background: none; border: none; color: #c0392b; cursor: pointer; padding: 0 0.25rem; }
.cart-footer { padding: 0.75rem; border-top: 1px solid #e0e0e0; }
.cart-total { font-size: 1.1rem; margin-bottom: 0.5rem; display: flex; justify-content: space-between; }
.order-btn { width: 100%; padding: 0.85rem; background: #27ae60; color: #fff; border: none; border-radius: 8px; font-size: 1.05rem; cursor: pointer; }
.order-btn:disabled { background: #bdc3c7; cursor: not-allowed; }

.confirm-phase { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1.25rem; padding: 2rem; }
h2 { font-size: 1.8rem; }
.summary { width: 100%; max-width: 480px; background: #fff; border-radius: 12px; padding: 1.25rem; }
.sum-line, .sum-total { display: flex; justify-content: space-between; padding: 0.4rem 0; border-bottom: 1px solid #f0f0f0; }
.sum-total { font-size: 1.2rem; font-weight: 700; border-bottom: none; padding-top: 0.75rem; }
.pager-row { width: 100%; max-width: 480px; }
.pager-row label { display: block; font-size: 0.9rem; color: #555; margin-bottom: 0.3rem; }
.pager-row input { width: 100%; border: 2px solid #ddd; border-radius: 8px; padding: 0.6rem; font-size: 1.2rem; }
.confirm-actions { display: flex; gap: 1rem; width: 100%; max-width: 480px; }
.back-btn, .submit-btn { flex: 1; padding: 0.85rem; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; }
.back-btn { background: #ecf0f1; }
.submit-btn { background: #27ae60; color: #fff; }
.submit-btn:disabled { background: #bdc3c7; cursor: not-allowed; }

.success-phase { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1rem; text-align: center; }
.success-icon { font-size: 5rem; color: #27ae60; }
h1 { font-size: 2.2rem; }
.countdown { color: #aaa; font-size: 0.95rem; border: 1px solid #eee; padding: 0.3rem 1rem; border-radius: 20px; margin-top: 1rem; }
</style>
