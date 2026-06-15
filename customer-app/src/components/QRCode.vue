<template>
  <canvas ref="canvas" :width="size" :height="size" class="qr-canvas" />
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import QRCode from 'qrcode'

const props = defineProps<{ value: string; size?: number }>()
const canvas = ref<HTMLCanvasElement | null>(null)
const sz = props.size ?? 200

async function render() {
  if (!canvas.value || !props.value) return
  await QRCode.toCanvas(canvas.value, props.value, {
    width: sz,
    margin: 2,
    color: { dark: '#1a1a2e', light: '#ffffff' },
  })
}

onMounted(render)
watch(() => props.value, render)
</script>

<style scoped>
.qr-canvas {
  border-radius: 12px;
  display: block;
}
</style>
