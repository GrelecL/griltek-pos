import type { Category, Product, Price } from '../types'

const BASE = (import.meta.env.VITE_STORE_API_URL as string) || 'http://localhost:8001'
const LOCATION_ID = (import.meta.env.VITE_LOCATION_ID as string) || ''
const TENANT_ID = (import.meta.env.VITE_TENANT_ID as string) || ''
const DEVICE_ID = (import.meta.env.VITE_DEVICE_ID as string) || 'kiosk-order-1'

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`)
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json() as Promise<T>
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json() as Promise<T>
}

export async function fetchCategories(): Promise<Category[]> {
  return get<Category[]>(`/api/v1/catalog/categories?tenant_id=${TENANT_ID}`)
}

export async function fetchProducts(categoryId?: string): Promise<Product[]> {
  const q = categoryId ? `?category_id=${categoryId}&tenant_id=${TENANT_ID}` : `?tenant_id=${TENANT_ID}`
  return get<Product[]>(`/api/v1/catalog/products${q}`)
}

export async function fetchPrice(productId: string): Promise<Price | null> {
  try {
    const prices = await get<Price[]>(`/api/v1/catalog/products/${productId}/prices`)
    return prices.find(p => p.price_type === 'regular') ?? prices[0] ?? null
  } catch {
    return null
  }
}

export interface OrderPayload {
  location_id: string
  user_id: string
  service_type: string
  pager_number: string | null
  lines: OrderLinePayload[]
}

export interface OrderLinePayload {
  product_id: string
  product_name: string
  plu: string
  qty: number
  unit_price: string
  vat_rate: string
  course: number | null
  modifiers: object[]
}

export async function submitOrder(payload: OrderPayload): Promise<{ id: string }> {
  return post<{ id: string }>('/api/v1/hospitality/orders', payload)
}

export { LOCATION_ID, DEVICE_ID }
