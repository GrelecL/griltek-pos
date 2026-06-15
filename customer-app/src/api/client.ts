const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

async function req<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('customer_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> ?? {}),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Request failed')
  }
  return res.json()
}

export interface AuthResponse {
  token: string
  customer: { id: string; name: string; email: string | null }
}

export interface LoyaltySummary {
  enrolled: boolean
  program_name?: string
  points_balance?: number
  points_lifetime?: number
  tier?: string
  redeem_value?: string
  next_tier?: string | null
  next_tier_points_needed?: number | null
  tiers?: Array<{ name: string; min_points: number; earn_multiplier: number }>
  customer_qr?: string
}

export interface ReceiptLine {
  product_name: string
  plu: string
  qty: string
  unit_price: string
  line_total: string
  vat_rate: string
}

export interface ReceiptPayment {
  method: string
  amount: string
}

export interface Receipt {
  id: string
  completed_at: string
  total: string
  subtotal: string
  vat_total: string
  discount_total: string
  sale_type: string
  lines: ReceiptLine[]
  payments: ReceiptPayment[]
}

export interface Coupon {
  id: string
  code: string
  name: string
  description: string | null
  discount_type: string
  discount_value: string
  min_purchase: string | null
  valid_until: string | null
  uses_remaining: number
}

export const api = {
  register: (body: { tenant_slug: string; phone?: string; email?: string; pin: string }) =>
    req<AuthResponse>('/customer-portal/register', { method: 'POST', body: JSON.stringify(body) }),

  login: (body: { tenant_slug: string; phone?: string; email?: string; pin: string }) =>
    req<AuthResponse>('/customer-portal/auth', { method: 'POST', body: JSON.stringify(body) }),

  me: () => req<{ id: string; name: string; email: string | null; phone: string | null }>('/customer-portal/me'),

  loyalty: () => req<LoyaltySummary>('/customer-portal/loyalty'),

  receipts: (limit = 20, offset = 0) =>
    req<Receipt[]>(`/customer-portal/receipts?limit=${limit}&offset=${offset}`),

  receipt: (id: string) => req<Receipt>(`/customer-portal/receipts/${id}`),

  coupons: () => req<Coupon[]>('/customer-portal/coupons'),
}
