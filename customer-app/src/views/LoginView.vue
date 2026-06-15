<template>
  <div class="login-page">
    <div class="login-header">
      <div class="logo">🎁</div>
      <h1>Zvestobni program</h1>
      <p>Prijavite se ali se registrirajte</p>
    </div>

    <div class="login-card">
      <div class="tabs">
        <button :class="{ active: mode === 'login' }" @click="mode = 'login'">Prijava</button>
        <button :class="{ active: mode === 'register' }" @click="mode = 'register'">Registracija</button>
      </div>

      <div class="form">
        <div class="field">
          <label>Naziv trgovine</label>
          <input v-model="slug" type="text" placeholder="npr. moja-trgovina" autocomplete="off" />
        </div>

        <div class="field">
          <label>Telefon ali e-mail</label>
          <input v-model="contact" type="text" placeholder="+38641... ali ime@email.si" autocomplete="off" />
        </div>

        <div class="field">
          <label>PIN (4 številke)</label>
          <input v-model="pin" type="password" inputmode="numeric" maxlength="6" placeholder="••••" />
        </div>

        <p v-if="error" class="error-msg">{{ error }}</p>

        <button class="btn-primary" :disabled="loading || !canSubmit" @click="submit">
          <span v-if="loading">Nalaganje…</span>
          <span v-else>{{ mode === 'login' ? 'Prijava' : 'Registracija' }}</span>
        </button>
      </div>

      <p class="hint">
        {{ mode === 'login' ? 'Nimate računa?' : 'Že imate račun?' }}
        <button class="link" @click="mode = mode === 'login' ? 'register' : 'login'">
          {{ mode === 'login' ? 'Registrirajte se' : 'Prijavite se' }}
        </button>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const mode = ref<'login' | 'register'>('login')
const slug = ref(auth.tenantSlug || '')
const contact = ref('')
const pin = ref('')
const error = ref('')
const loading = ref(false)

const canSubmit = computed(() => slug.value && contact.value && pin.value.length >= 4)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    if (mode.value === 'login') {
      await auth.login(slug.value.trim(), contact.value.trim(), pin.value)
    } else {
      await auth.register(slug.value.trim(), contact.value.trim(), pin.value)
    }
    router.replace('/card')
  } catch (e: any) {
    error.value = e.message ?? 'Napaka pri prijavi'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(160deg, var(--brand) 0%, var(--brand-dark) 40%, var(--bg) 100%);
  display: flex;
  flex-direction: column;
  padding: 48px 20px 32px;
}

.login-header {
  text-align: center;
  color: #fff;
  margin-bottom: 32px;
}
.logo { font-size: 52px; margin-bottom: 12px; }
.login-header h1 { font-size: 26px; font-weight: 700; margin-bottom: 6px; }
.login-header p { opacity: 0.85; font-size: 15px; }

.login-card {
  background: var(--surface);
  border-radius: 24px;
  padding: 24px 20px;
  box-shadow: 0 8px 32px rgba(0,0,0,.15);
}

.tabs {
  display: flex;
  background: var(--bg);
  border-radius: 12px;
  padding: 4px;
  margin-bottom: 24px;
}
.tabs button {
  flex: 1;
  padding: 10px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 500;
  color: var(--muted);
  transition: all 0.2s;
}
.tabs button.active {
  background: var(--surface);
  color: var(--text);
  font-weight: 600;
  box-shadow: 0 1px 4px rgba(0,0,0,.1);
}

.form { display: flex; flex-direction: column; gap: 16px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field label { font-size: 13px; font-weight: 600; color: var(--muted); padding-left: 4px; }

.error-msg {
  color: #e53e3e;
  font-size: 14px;
  text-align: center;
  padding: 8px;
  background: #fff5f5;
  border-radius: 8px;
}

.hint {
  text-align: center;
  margin-top: 16px;
  font-size: 14px;
  color: var(--muted);
}
.link { color: var(--brand); font-weight: 600; padding: 0 4px; }
</style>
