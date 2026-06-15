<template>
  <div class="receipt-screen">
    <div class="icon">✓</div>
    <h1>Hvala za nakup!</h1>
    <p class="total">Skupaj plačano: <strong>{{ total.toFixed(2) }} €</strong></p>
    <p v-if="change > 0" class="change">Vračilo: <strong>{{ change.toFixed(2) }} €</strong></p>
    <p class="sub">Vzamite račun pri blagajni ali počakajte na tiskanje.</p>
    <div class="countdown">Nova seja čez {{ countdown }}s</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps<{ total: number; change: number }>()
const emit = defineEmits<{ (e: 'done'): void }>()

const countdown = ref(8)
let timer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      if (timer) clearInterval(timer)
      emit('done')
    }
  }, 1000)
})

onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.receipt-screen { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center; gap: 1rem; }
.icon { font-size: 5rem; color: #27ae60; }
h1 { font-size: 2.5rem; margin: 0; }
.total { font-size: 1.5rem; margin: 0; }
.change { font-size: 1.3rem; color: #27ae60; margin: 0; }
.sub { color: #888; margin: 0; }
.countdown { margin-top: 1rem; font-size: 0.95rem; color: #aaa; border: 1px solid #eee; border-radius: 20px; padding: 0.3rem 1rem; }
</style>
