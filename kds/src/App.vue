<template>
  <div class="kds-layout">
    <header class="kds-header">
      <span class="brand">KDS — Kuhinja</span>
      <span class="station-label" v-if="station">Postaja: {{ station }}</span>
      <span :class="['ws-status', wsConnected ? 'ok' : 'err']">
        {{ wsConnected ? '● Povezan' : '○ Ni povezave' }}
      </span>
      <span class="clock">{{ clock }}</span>
    </header>

    <main class="board">
      <div v-if="lines.length === 0" class="empty">
        <p>Ni aktivnih naročil</p>
      </div>
      <div
        v-for="line in lines"
        :key="line.id"
        :class="['ticket', `status-${line.kds_status}`, line.kds_status === 'ready' ? 'blink' : '']"
      >
        <div class="ticket-header">
          <span class="order-ref">{{ line.order_id.slice(-6).toUpperCase() }}</span>
          <span v-if="line.course" class="course">Hod {{ line.course }}</span>
          <span class="elapsed">{{ elapsed(line.fired_at) }}</span>
        </div>
        <div class="product-name">{{ line.product_name }}</div>
        <div class="qty">× {{ line.qty }}</div>
        <div v-if="line.modifiers?.length" class="mods">
          {{ line.modifiers.map((m: any) => m.option).join(', ') }}
        </div>
        <div v-if="line.note" class="note">📝 {{ line.note }}</div>

        <div class="ticket-actions">
          <button
            v-if="line.kds_status === 'in_kitchen'"
            class="action-btn ready-btn"
            @click="updateStatus(line.id, 'ready')"
          >Pripravljeno</button>
          <button
            v-if="line.kds_status === 'ready'"
            class="action-btn served-btn"
            @click="updateStatus(line.id, 'served')"
          >Postreženo</button>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import type { KDSLine } from './types'

const BASE = (import.meta.env.VITE_STORE_API_URL as string) || 'http://localhost:8001'
const WS_URL = BASE.replace(/^http/, 'ws') + '/api/v1/hospitality/kds/ws'
const LOCATION_ID = (import.meta.env.VITE_LOCATION_ID as string) || ''
const station = (import.meta.env.VITE_KDS_STATION as string) || ''

const lines = ref<KDSLine[]>([])
const wsConnected = ref(false)
const clock = ref('')

let ws: WebSocket | null = null
let clockTimer: ReturnType<typeof setInterval> | null = null
let pollTimer: ReturnType<typeof setInterval> | null = null

// ── HTTP poll for initial load + fallback ─────────────────────────────────────
async function poll() {
  try {
    const q = station ? `?location_id=${LOCATION_ID}&station=${station}` : `?location_id=${LOCATION_ID}`
    const r = await fetch(`${BASE}/api/v1/hospitality/kds/lines${q}`)
    if (r.ok) {
      lines.value = await r.json()
    }
  } catch {
    // offline — keep showing last known state
  }
}

// ── WebSocket ─────────────────────────────────────────────────────────────────
function connectWS() {
  ws = new WebSocket(WS_URL)
  ws.onopen = () => { wsConnected.value = true }
  ws.onclose = () => {
    wsConnected.value = false
    setTimeout(connectWS, 3000)
  }
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data as string)
    if (msg.event === 'line_updated') {
      const updated: KDSLine = msg.line
      const idx = lines.value.findIndex(l => l.id === updated.id)
      if (updated.kds_status === 'served') {
        // remove from board when served
        if (idx >= 0) lines.value.splice(idx, 1)
      } else if (idx >= 0) {
        lines.value[idx] = updated
      } else if (updated.kds_status === 'in_kitchen' || updated.kds_status === 'ready') {
        lines.value.push(updated)
      }
    }
  }
}

// ── status update (also sent via WS; HTTP PATCH for non-WS fallback) ─────────
async function updateStatus(lineId: string, status: string) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: 'status_update', line_id: lineId, status }))
  } else {
    await fetch(`${BASE}/api/v1/hospitality/kds/lines/${lineId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    })
    await poll()
  }
}

function elapsed(firedAt: string | null): string {
  if (!firedAt) return ''
  const secs = Math.floor((Date.now() - new Date(firedAt).getTime()) / 1000)
  const m = Math.floor(secs / 60)
  const s = secs % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

onMounted(() => {
  poll()
  pollTimer = setInterval(poll, 10000)
  connectWS()
  clockTimer = setInterval(() => {
    const now = new Date()
    clock.value = now.toLocaleTimeString('sl-SI')
  }, 1000)
})

onUnmounted(() => {
  ws?.close()
  if (clockTimer) clearInterval(clockTimer)
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: #111; color: #fff; height: 100vh; overflow: hidden; }
#app { height: 100vh; }
</style>

<style scoped>
.kds-layout { display: flex; flex-direction: column; height: 100vh; }
.kds-header { background: #0d1b2a; display: flex; align-items: center; gap: 1.5rem; padding: 0.75rem 1.5rem; flex-shrink: 0; }
.brand { font-weight: 700; font-size: 1.1rem; }
.station-label { background: #1e3a5f; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.9rem; }
.ws-status { font-size: 0.85rem; }
.ws-status.ok { color: #27ae60; }
.ws-status.err { color: #e74c3c; }
.clock { margin-left: auto; font-size: 1.1rem; font-variant-numeric: tabular-nums; }

.board { flex: 1; display: flex; flex-wrap: wrap; align-content: flex-start; gap: 1rem; padding: 1rem; overflow-y: auto; }
.empty { width: 100%; text-align: center; color: #555; padding: 4rem; font-size: 1.3rem; }

.ticket { width: 220px; border-radius: 10px; padding: 1rem; display: flex; flex-direction: column; gap: 0.5rem; }
.ticket.status-in_kitchen { background: #1e3a5f; border: 2px solid #2980b9; }
.ticket.status-ready { background: #1a3a1a; border: 2px solid #27ae60; }
.ticket.blink { animation: blink 1s step-start infinite; }
@keyframes blink { 50% { border-color: transparent; } }

.ticket-header { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8rem; color: #aaa; }
.order-ref { font-family: monospace; font-weight: 700; color: #7fb3d3; }
.course { background: #2c3e50; padding: 0.1rem 0.4rem; border-radius: 4px; }
.elapsed { margin-left: auto; }
.product-name { font-size: 1.2rem; font-weight: 700; }
.qty { font-size: 1.5rem; font-weight: 900; color: #f39c12; }
.mods { font-size: 0.8rem; color: #888; }
.note { font-size: 0.85rem; color: #e67e22; }

.ticket-actions { margin-top: auto; }
.action-btn { width: 100%; padding: 0.6rem; border: none; border-radius: 6px; cursor: pointer; font-size: 0.95rem; font-weight: 700; }
.ready-btn { background: #27ae60; color: #fff; }
.served-btn { background: #7f8c8d; color: #fff; }
</style>
