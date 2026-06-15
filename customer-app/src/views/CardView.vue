<template>
  <div class="page">
    <div class="page-title">Moja kartica</div>

    <!-- Loyalty card -->
    <div class="loyalty-card" :class="tierClass">
      <div class="card-header">
        <div class="card-name">{{ auth.customer?.name }}</div>
        <div class="tier-badge" v-if="loyalty?.tier">{{ tierLabel }}</div>
      </div>

      <div class="card-points" v-if="loyalty?.enrolled">
        <span class="pts-number">{{ loyalty.points_balance?.toLocaleString('sl-SI') }}</span>
        <span class="pts-label">točk</span>
      </div>
      <div class="card-points no-prog" v-else>
        <span class="pts-label">Zvestobni program ni aktiven</span>
      </div>

      <div class="card-prog" v-if="loyalty?.next_tier && loyalty?.next_tier_points_needed">
        <div class="prog-bar-bg">
          <div class="prog-bar-fill" :style="{ width: progressPct + '%' }" />
        </div>
        <div class="prog-label">
          Še {{ loyalty.next_tier_points_needed }} točk do stopnje <strong>{{ loyalty.next_tier }}</strong>
        </div>
      </div>

      <div class="card-brand">Griltek POS</div>
    </div>

    <!-- redeem value -->
    <div class="card" v-if="loyalty?.enrolled && loyalty.redeem_value !== '0.00'">
      <div class="redeem-row">
        <div>
          <div class="redeem-label">Vrednost točk</div>
          <div class="redeem-value">€ {{ loyalty.redeem_value }}</div>
        </div>
        <div class="redeem-icon">💶</div>
      </div>
    </div>

    <!-- QR code for scanning at POS -->
    <div class="card qr-card" v-if="loyalty?.customer_qr">
      <div class="qr-title">Skenirajte pri blagajni</div>
      <div class="qr-wrap">
        <QRCode :value="loyalty.customer_qr" :size="180" />
      </div>
      <div class="qr-id">ID: {{ shortId }}</div>
    </div>

    <button class="logout-btn" @click="logout">Odjava</button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { api, type LoyaltySummary } from '../api/client'
import QRCode from '../components/QRCode.vue'

const auth = useAuthStore()
const router = useRouter()
const loyalty = ref<LoyaltySummary | null>(null)

onMounted(async () => {
  try { loyalty.value = await api.loyalty() } catch {}
})

const tierClass = computed(() => {
  const t = loyalty.value?.tier ?? 'standard'
  return `tier-${t}`
})

const tierLabel = computed(() => {
  const map: Record<string, string> = {
    standard: 'Standardna', silver: 'Srebrna', gold: 'Zlata', platinum: 'Platinasta',
  }
  return map[loyalty.value?.tier ?? 'standard'] ?? loyalty.value?.tier ?? ''
})

const progressPct = computed(() => {
  const loy = loyalty.value
  if (!loy?.tiers || !loy.next_tier || !loy.next_tier_points_needed) return 0
  const tiers = [...loy.tiers].sort((a, b) => a.min_points - b.min_points)
  const curTierIdx = tiers.findIndex(t => t.name === loy.tier)
  const curMin = tiers[curTierIdx]?.min_points ?? 0
  const nextMin = curMin + (loy.next_tier_points_needed ?? 0)
  const pct = ((loy.points_lifetime! - curMin) / (nextMin - curMin)) * 100
  return Math.min(Math.max(pct, 0), 100)
})

const shortId = computed(() => loyalty.value?.customer_qr?.slice(0, 8) ?? '')

function logout() {
  auth.logout()
  router.replace('/login')
}
</script>

<style scoped>
.loyalty-card {
  margin: 8px 16px 0;
  border-radius: 20px;
  padding: 24px 22px 20px;
  background: var(--tier-standard);
  color: #fff;
  min-height: 180px;
  position: relative;
  overflow: hidden;
}
.loyalty-card.tier-silver { background: var(--tier-silver); color: #1a1a2e; }
.loyalty-card.tier-gold { background: var(--tier-gold); color: #1a1a2e; }
.loyalty-card.tier-platinum { background: var(--tier-platinum); color: #fff; }
.loyalty-card::before {
  content: '';
  position: absolute;
  top: -40px; right: -40px;
  width: 160px; height: 160px;
  border-radius: 50%;
  background: rgba(255,255,255,.08);
}

.card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.card-name { font-size: 18px; font-weight: 700; }
.tier-badge {
  background: rgba(255,255,255,.25);
  backdrop-filter: blur(4px);
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.card-points { display: flex; align-items: baseline; gap: 6px; margin-bottom: 16px; }
.pts-number { font-size: 42px; font-weight: 800; line-height: 1; }
.pts-label { font-size: 16px; font-weight: 500; opacity: 0.8; }
.card-points.no-prog .pts-label { font-size: 14px; }

.prog-bar-bg {
  height: 6px;
  background: rgba(255,255,255,.25);
  border-radius: 999px;
  overflow: hidden;
  margin-bottom: 6px;
}
.prog-bar-fill {
  height: 100%;
  background: rgba(255,255,255,.8);
  border-radius: 999px;
  transition: width 0.8s ease;
}
.prog-label { font-size: 12px; opacity: 0.85; }

.card-brand {
  position: absolute;
  bottom: 16px; right: 20px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  opacity: 0.5;
}

.redeem-row { display: flex; justify-content: space-between; align-items: center; }
.redeem-label { font-size: 13px; color: var(--muted); margin-bottom: 4px; }
.redeem-value { font-size: 26px; font-weight: 800; color: var(--brand); }
.redeem-icon { font-size: 32px; }

.qr-card { text-align: center; }
.qr-title { font-size: 14px; font-weight: 600; color: var(--muted); margin-bottom: 16px; }
.qr-wrap { display: flex; justify-content: center; margin-bottom: 8px; }
.qr-id { font-size: 12px; color: var(--muted); font-family: monospace; }

.logout-btn {
  display: block;
  width: calc(100% - 32px);
  margin: 8px 16px 0;
  padding: 14px;
  border-radius: 14px;
  font-size: 15px;
  font-weight: 500;
  color: var(--muted);
  background: var(--surface);
  border: 1.5px solid var(--border);
}
</style>
