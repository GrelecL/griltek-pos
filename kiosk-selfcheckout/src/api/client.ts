import type { Product, Price, SalePayload } from '../types'

const BASE = (import.meta.env.VITE_STORE_API_URL as string) || 'http://localhost:8001'
const LOCATION_ID = (import.meta.env.VITE_LOCATION_ID as string) || ''
const DEVICE_ID = (import.meta.env.VITE_DEVICE_ID as string) || 'kiosk-selfcheckout-1'
const TENANT_ID = (import.meta.env.VITE_TENANT_ID as string) || ''

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`)
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${path}`)
  return r.json() as Promise<T>
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${path}`)
  return r.json() as Promise<T>
}

export async function lookupBarcode(code: string): Promise<Product> {
  return get<Product>(`/api/v1/catalog/products/by-barcode/${encodeURIComponent(code)}`)
}

export async function lookupPlu(plu: string): Promise<Product> {
  return get<Product>(
    `/api/v1/catalog/products/by-plu/${encodeURIComponent(plu)}?tenant_id=${TENANT_ID}`
  )
}

export async function fetchPrices(productId: string): Promise<Price[]> {
  return get<Price[]>(`/api/v1/catalog/products/${productId}/prices`)
}

export async function createSale(payload: SalePayload): Promise<{ id: string }> {
  return post<{ id: string }>('/api/v1/pos/sales', payload)
}

export async function verifyAttendantPin(pin: string): Promise<boolean> {
  try {
    const res = await post<{ access_token?: string }>('/api/v1/auth/pin-login', {
      pin,
      location_id: LOCATION_ID,
      device_id: DEVICE_ID,
    })
    return !!res.access_token
  } catch {
    return false
  }
}

export async function sendHeartbeat(): Promise<void> {
  try {
    await post(`/heartbeat/device/${DEVICE_ID}`, { location_id: LOCATION_ID })
  } catch {
    // non-critical
  }
}

export { LOCATION_ID, DEVICE_ID, TENANT_ID }
