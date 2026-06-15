<template>
  <div class="page">
    <div class="page-title">Moji kuponi</div>
    <div class="page-sub">Pokažite QR kodo blagajniku pri plačilu</div>

    <div v-if="loading" class="empty">Nalaganje…</div>
    <div v-else-if="!coupons.length" class="empty">
      <div style="font-size:40px;margin-bottom:12px">🎫</div>
      Trenutno nimate razpoložljivih kuponov
    </div>

    <div v-else class="coupons-list">
      <div v-for="c in coupons" :key="c.id" class="coupon-card" @click="toggle(c.id)">
        <div class="coupon-header">
          <div class="coupon-discount">{{ formatDiscount(c) }}</div>
          <div class="coupon-chevron" :class="{ open: expanded === c.id }">›</div>
        </div>

        <div class="coupon-name">{{ c.name }}</div>
        <div v-if="c.description" class="coupon-desc">{{ c.description }}</div>

        <div class="coupon-meta">
          <span v-if="c.min_purchase" class="chip chip-gray">Min. nakup €{{ c.min_purchase }}</span>
          <span v-if="c.valid_until" class="chip chip-gray">Do {{ formatDate(c.valid_until) }}</span>
          <span class="chip chip-green">Še {{ c.uses_remaining }}× na voljo</span>
        </div>

        <!-- QR code expands on tap -->
        <Transition name="slide">
          <div v-if="expanded === c.id" class="coupon-qr">
            <div class="qr-label">Skenirajte pri blagajni</div>
            <div class="qr-center">
              <QRCode :value="c.code" :size="180" />
            </div>
            <div class="coupon-code">{{ c.code }}</div>
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type Coupon } from '../api/client'
import QRCode from '../components/QRCode.vue'

const coupons = ref<Coupon[]>([])
const loading = ref(true)
const expanded = ref<string | null>(null)

onMounted(async () => {
  try { coupons.value = await api.coupons() } catch {}
  finally { loading.value = false }
})

function toggle(id: string) {
  expanded.value = expanded.value === id ? null : id
}

function formatDiscount(c: Coupon): string {
  if (c.discount_type === 'pct_discount') return `-${c.discount_value}%`
  if (c.discount_type === 'fixed_discount') return `-€${c.discount_value}`
  return 'Brezplačen artikel'
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('sl-SI', { day: 'numeric', month: 'short', year: 'numeric' })
}
</script>

<style scoped>
.coupons-list { padding: 0 16px; display: flex; flex-direction: column; gap: 12px; }

.coupon-card {
  background: var(--surface);
  border-radius: var(--radius);
  padding: 18px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
  cursor: pointer;
  user-select: none;
  border: 2px solid transparent;
  transition: border-color 0.2s;
}
.coupon-card:has(.coupon-qr) { border-color: var(--brand); }

.coupon-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.coupon-discount {
  font-size: 28px;
  font-weight: 800;
  color: var(--brand);
}
.coupon-chevron {
  font-size: 24px;
  color: var(--muted);
  transform: rotate(90deg);
  transition: transform 0.25s;
}
.coupon-chevron.open { transform: rotate(-90deg); }

.coupon-name { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.coupon-desc { font-size: 13px; color: var(--muted); margin-bottom: 10px; }

.coupon-meta { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.chip-gray { background: var(--bg); color: var(--muted); }
.chip-green { background: #ecfdf5; color: #065f46; }

.coupon-qr { margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border); text-align: center; }
.qr-label { font-size: 13px; color: var(--muted); margin-bottom: 12px; }
.qr-center { display: flex; justify-content: center; margin-bottom: 10px; }
.coupon-code {
  font-family: monospace;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 2px;
  color: var(--brand);
  background: var(--bg);
  padding: 8px 16px;
  border-radius: 8px;
  display: inline-block;
}

.slide-enter-active, .slide-leave-active { transition: all 0.25s ease; overflow: hidden; }
.slide-enter-from, .slide-leave-to { opacity: 0; max-height: 0; margin-top: 0; }
.slide-enter-to, .slide-leave-from { opacity: 1; max-height: 400px; }
</style>
