import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/', redirect: '/card' },
  { path: '/login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
  { path: '/card', component: () => import('../views/CardView.vue') },
  { path: '/coupons', component: () => import('../views/CouponsView.vue') },
  { path: '/receipts', component: () => import('../views/ReceiptsView.vue') },
  { path: '/receipts/:id', component: () => import('../views/ReceiptDetailView.vue') },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isLoggedIn) return '/login'
})
