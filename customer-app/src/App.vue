<template>
  <RouterView />
  <BottomNav v-if="auth.isLoggedIn" />
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import BottomNav from './components/BottomNav.vue'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
</script>
