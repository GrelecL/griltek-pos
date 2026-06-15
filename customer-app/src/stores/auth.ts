import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '../api/client'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('customer_token'))
  const customer = ref<{ id: string; name: string; email: string | null } | null>(
    JSON.parse(localStorage.getItem('customer_data') ?? 'null')
  )
  const tenantSlug = ref<string>(localStorage.getItem('tenant_slug') ?? '')

  const isLoggedIn = computed(() => !!token.value)

  function _persist(t: string, c: typeof customer.value) {
    token.value = t
    customer.value = c
    localStorage.setItem('customer_token', t)
    localStorage.setItem('customer_data', JSON.stringify(c))
  }

  async function login(slug: string, contact: string, pin: string) {
    const isEmail = contact.includes('@')
    const body = {
      tenant_slug: slug,
      [isEmail ? 'email' : 'phone']: contact,
      pin,
    }
    const res = await api.login(body)
    tenantSlug.value = slug
    localStorage.setItem('tenant_slug', slug)
    _persist(res.token, res.customer)
  }

  async function register(slug: string, contact: string, pin: string) {
    const isEmail = contact.includes('@')
    const body = {
      tenant_slug: slug,
      [isEmail ? 'email' : 'phone']: contact,
      pin,
    }
    const res = await api.register(body)
    tenantSlug.value = slug
    localStorage.setItem('tenant_slug', slug)
    _persist(res.token, res.customer)
  }

  function logout() {
    token.value = null
    customer.value = null
    localStorage.removeItem('customer_token')
    localStorage.removeItem('customer_data')
    localStorage.removeItem('tenant_slug')
  }

  return { token, customer, tenantSlug, isLoggedIn, login, register, logout }
})
