<template>
  <div class="stat-card">
    <div class="label">{{ label }}</div>
    <div class="value">{{ value }}</div>
    <div v-if="sub" class="sub">{{ sub }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ label: string; value: string | number; sub?: string }>()
</script>

<style scoped>
.stat-card { background: #fff; border-radius: 10px; padding: 1.25rem 1.5rem; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.label { font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 0.25rem; }
.value { font-size: 1.8rem; font-weight: 700; color: #1a2a3a; }
.sub { font-size: 0.8rem; color: #aaa; margin-top: 0.25rem; }
</style>
