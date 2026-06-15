<template>
  <div class="data-table">
    <div class="table-header">
      <h3>{{ title }}</h3>
      <a v-if="downloadUrl" :href="downloadUrl" class="csv-btn" download>↓ CSV</a>
    </div>
    <div v-if="loading" class="loading">Nalagam...</div>
    <div v-else-if="rows.length === 0" class="empty">Ni podatkov</div>
    <table v-else>
      <thead>
        <tr><th v-for="col in columns" :key="col.key">{{ col.label }}</th></tr>
      </thead>
      <tbody>
        <tr v-for="(row, i) in rows" :key="i">
          <td v-for="col in columns" :key="col.key">{{ row[col.key] }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  columns: Array<{ key: string; label: string }>
  rows: Array<Record<string, unknown>>
  loading?: boolean
  downloadUrl?: string
}>()
</script>

<style scoped>
.data-table { background: #fff; border-radius: 10px; box-shadow: 0 1px 4px rgba(0,0,0,.08); overflow: hidden; }
.table-header { display: flex; justify-content: space-between; align-items: center; padding: 1rem 1.25rem; border-bottom: 1px solid #f0f0f0; }
h3 { margin: 0; font-size: 1rem; }
.csv-btn { font-size: 0.85rem; color: #2980b9; text-decoration: none; background: #ebf5fb; padding: 0.3rem 0.75rem; border-radius: 6px; }
.loading, .empty { padding: 1.5rem; text-align: center; color: #aaa; font-size: 0.9rem; }
table { width: 100%; border-collapse: collapse; }
th { background: #f8f8f8; padding: 0.6rem 1rem; text-align: left; font-size: 0.8rem; color: #666; text-transform: uppercase; letter-spacing: .04em; }
td { padding: 0.6rem 1rem; border-bottom: 1px solid #f5f5f5; font-size: 0.9rem; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #fafafa; }
</style>
