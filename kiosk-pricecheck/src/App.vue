<template>
  <div class="pricecheck-layout">
    <header>
      <span class="brand">Griltek POS — Preverba cen</span>
    </header>

    <main class="main">
      <div v-if="state === 'idle'" class="idle">
        <div class="idle-icon">🏷️</div>
        <h1>Skenirajte artikel</h1>
        <p>Prinesite artikel k bralcu črtne kode</p>
      </div>

      <div v-else-if="state === 'loading'" class="loading">
        <div class="spinner"></div>
        <p>Iščem artikel...</p>
      </div>

      <div v-else-if="state === 'result' && product" class="result">
        <div class="product-card">
          <div class="product-name">{{ product.name }}</div>
          <div class="product-plu">Šifra: {{ product.plu }}</div>
          <div class="price-display">
            <span class="amount">{{ parseFloat(price).toFixed(2) }}</span>
            <span class="unit">€<span v-if="product.is_weighable">/kg</span></span>
          </div>
          <div class="vat-line">Cena vključuje {{ product.vat_rate }}% DDV</div>
          <div v-if="product.allergens?.length" class="allergens">
            <span class="allergen-label">Alergeni:</span>
            {{ product.allergens.join(', ') }}
          </div>
          <div v-if="product.age_restricted" class="age-badge">
            🔞 Starost {{ product.min_age }}+
          </div>
        </div>
        <p class="hint">Skenirajte naslednji artikel</p>
      </div>

      <div v-else-if="state === 'error'" class="error-state">
        <div class="error-icon">❌</div>
        <p>{{ errorMsg }}</p>
        <p class="hint">Skenirajte ponovo</p>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useScanner } from './useScanner'

interface Product {
  id: string; plu: string; name: string; vat_rate: string; unit: string
  is_weighable: boolean; age_restricted: boolean; min_age: number | null; allergens: string[]
}

const BASE = (import.meta.env.VITE_STORE_API_URL as string) || 'http://localhost:8001'

const state = ref<'idle' | 'loading' | 'result' | 'error'>('idle')
const product = ref<Product | null>(null)
const price = ref<string>('0.00')
const errorMsg = ref('')

let idleTimer: ReturnType<typeof setTimeout> | null = null

useScanner(async (code) => {
  if (idleTimer) clearTimeout(idleTimer)
  state.value = 'loading'
  product.value = null

  try {
    const pRes = await fetch(`${BASE}/api/v1/catalog/products/by-barcode/${encodeURIComponent(code)}`)
    if (!pRes.ok) throw new Error('not_found')
    const p: Product = await pRes.json()
    product.value = p

    const prRes = await fetch(`${BASE}/api/v1/catalog/products/${p.id}/prices`)
    const prices: Array<{ price_type: string; amount: string }> = await prRes.json()
    const regular = prices.find(x => x.price_type === 'regular') ?? prices[0]
    price.value = regular?.amount ?? '—'

    state.value = 'result'
  } catch {
    errorMsg.value = 'Artikel ni najden.'
    state.value = 'error'
  }

  idleTimer = setTimeout(() => { state.value = 'idle' }, 10000)
})
</script>

<script lang="ts">
// Inline scanner composable (same logic as selfcheckout, no shared lib needed here)
export {}
</script>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: #1a2a3a; color: #fff; height: 100vh; overflow: hidden; }
#app { height: 100vh; }
</style>

<style scoped>
.pricecheck-layout { display: flex; flex-direction: column; height: 100vh; }
header { background: #0d1b2a; padding: 1rem 1.5rem; font-size: 1rem; }
.brand { font-weight: 700; color: #7fb3d3; }
.main { flex: 1; display: flex; align-items: center; justify-content: center; }

/* Idle */
.idle { text-align: center; }
.idle-icon { font-size: 6rem; margin-bottom: 1rem; }
h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
p { font-size: 1.1rem; color: #aaa; }
.hint { margin-top: 1.5rem; font-size: 1rem; color: #888; }

/* Loading */
.loading { text-align: center; }
.spinner { width: 60px; height: 60px; border: 6px solid #334; border-top-color: #5b9bd5; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 1rem; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Result */
.result { text-align: center; }
.product-card { background: #1e3a5f; border-radius: 16px; padding: 2.5rem 3rem; display: inline-block; min-width: 360px; }
.product-name { font-size: 2rem; font-weight: 700; margin-bottom: 0.25rem; }
.product-plu { font-size: 0.9rem; color: #7fb3d3; margin-bottom: 1.5rem; }
.price-display { font-size: 3.5rem; font-weight: 900; color: #27ae60; line-height: 1; margin-bottom: 0.5rem; }
.amount { margin-right: 0.15rem; }
.unit { font-size: 1.5rem; font-weight: 400; color: #7fb3d3; }
.vat-line { font-size: 0.85rem; color: #888; margin-bottom: 1rem; }
.allergens { font-size: 0.9rem; color: #e67e22; margin-bottom: 0.75rem; }
.allergen-label { font-weight: 700; }
.age-badge { display: inline-block; background: #c0392b; padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.9rem; }

/* Error */
.error-state { text-align: center; }
.error-icon { font-size: 5rem; margin-bottom: 1rem; }
</style>
