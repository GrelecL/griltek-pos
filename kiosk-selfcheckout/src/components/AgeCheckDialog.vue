<template>
  <div class="overlay">
    <div class="dialog">
      <div class="icon">🔞</div>
      <h2>Starostna omejitev</h2>
      <p>Ta artikel zahteva potrditev starosti ({{ minAge }}+).<br>Prosimo počakajte na osebje.</p>

      <div v-if="!awaitingPin">
        <p class="sub">Osebje: vnesite PIN za potrditev.</p>
        <button class="staff-btn" @click="awaitingPin = true">Vnesi PIN</button>
        <button class="cancel" @click="$emit('denied')">Zavrni artikel</button>
      </div>

      <div v-else>
        <div class="pin-dots">
          <span v-for="i in 4" :key="i" :class="{ filled: pin.length >= i }">●</span>
        </div>
        <div class="keypad">
          <button v-for="d in digits" :key="d" @click="appendPin(d)">{{ d }}</button>
          <button class="clear" @click="pin = ''">C</button>
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <button class="cancel" @click="awaitingPin = false; pin = ''; error = ''">Nazaj</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { verifyAttendantPin } from '../api/client'

const props = defineProps<{ minAge: number }>()
const emit = defineEmits<{
  (e: 'approved', attendantPin: string): void
  (e: 'denied'): void
}>()

const awaitingPin = ref(false)
const pin = ref('')
const error = ref('')
const digits = ['1','2','3','4','5','6','7','8','9','0']

async function appendPin(d: string) {
  if (pin.value.length >= 6) return
  pin.value += d
  if (pin.value.length >= 4) {
    const ok = await verifyAttendantPin(pin.value)
    if (ok) {
      emit('approved', pin.value)
    } else {
      error.value = 'Napačen PIN. Poskusite znova.'
      setTimeout(() => { pin.value = ''; error.value = '' }, 1200)
    }
  }
}
</script>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,.6); display: flex; align-items: center; justify-content: center; z-index: 200; }
.dialog { background: #fff; border-radius: 12px; padding: 2rem; width: 380px; text-align: center; }
.icon { font-size: 3rem; margin-bottom: 0.5rem; }
h2 { margin: 0 0 0.5rem; }
p { color: #555; margin: 0 0 1rem; }
.sub { font-size: 0.9rem; }
.staff-btn { display: block; width: 100%; padding: 0.8rem; background: #2c3e50; color: #fff; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; margin-bottom: 0.75rem; }
.cancel { display: block; width: 100%; padding: 0.6rem; background: #ecf0f1; border: none; border-radius: 8px; font-size: 0.95rem; cursor: pointer; margin-top: 0.5rem; }
.pin-dots { display: flex; justify-content: center; gap: 1rem; margin: 1rem 0; font-size: 1.5rem; }
.pin-dots span { color: #ddd; }
.pin-dots span.filled { color: #2c3e50; }
.keypad { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; margin-bottom: 0.75rem; }
.keypad button { padding: 0.8rem; font-size: 1.2rem; border: 1px solid #ddd; border-radius: 8px; cursor: pointer; background: #f8f8f8; }
.keypad button:active { background: #ddd; }
.clear { grid-column: 3; background: #ffeaea !important; color: #c0392b; }
.error { color: #c0392b; font-size: 0.9rem; margin-bottom: 0.5rem; }
</style>
