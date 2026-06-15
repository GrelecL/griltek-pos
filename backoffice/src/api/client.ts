const BASE = (import.meta.env.VITE_CLOUD_API_URL as string) || 'http://localhost:8000'

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

export interface DashboardData {
  period: { from: string; to: string }
  sales: { count: number; revenue: string }
  returns: { count: number; total: string }
  net_revenue: string
  pending_fiscal: number
}

export interface ProductRow {
  plu: string; product_name: string
  total_qty: string; total_revenue: string; total_vat: string
}

export interface PaymentRow {
  method: string; count: number; total: string
}

export interface VATRow {
  vat_rate: string; taxable: string; vat: string
}

export interface SyncHealth {
  pending_fiscal_records: number
  unsynced_stock_movements: number
  status: string
}

export async function fetchDashboard(locationId: string, dateFrom?: string, dateTo?: string): Promise<DashboardData> {
  const q = new URLSearchParams({ location_id: locationId })
  if (dateFrom) q.set('date_from', dateFrom)
  if (dateTo) q.set('date_to', dateTo)
  return get<DashboardData>(`/api/v1/reports/dashboard?${q}`)
}

export async function fetchSalesByProduct(locationId: string, dateFrom?: string, dateTo?: string): Promise<ProductRow[]> {
  const q = new URLSearchParams({ location_id: locationId })
  if (dateFrom) q.set('date_from', dateFrom)
  if (dateTo) q.set('date_to', dateTo)
  return get<ProductRow[]>(`/api/v1/reports/sales/by-product?${q}`)
}

export async function fetchPaymentBreakdown(locationId: string, dateFrom?: string, dateTo?: string): Promise<PaymentRow[]> {
  const q = new URLSearchParams({ location_id: locationId })
  if (dateFrom) q.set('date_from', dateFrom)
  if (dateTo) q.set('date_to', dateTo)
  return get<PaymentRow[]>(`/api/v1/reports/sales/payments?${q}`)
}

export async function fetchVATBreakdown(locationId: string, dateFrom?: string, dateTo?: string): Promise<VATRow[]> {
  const q = new URLSearchParams({ location_id: locationId })
  if (dateFrom) q.set('date_from', dateFrom)
  if (dateTo) q.set('date_to', dateTo)
  return get<VATRow[]>(`/api/v1/reports/sales/vat?${q}`)
}

export async function fetchSyncHealth(): Promise<SyncHealth> {
  return get<SyncHealth>('/api/v1/admin/sync-health')
}

export function csvUrl(path: string, params: Record<string, string>): string {
  const q = new URLSearchParams({ ...params, fmt: 'csv' })
  return `${BASE}${path}?${q}`
}

// ── Customers ─────────────────────────────────────────────────────────────────

export interface CustomerRow {
  id: string
  name: string
  phone: string | null
  email: string | null
  loyalty_points: number
  tier: string
}

export async function fetchCustomers(tenantId: string): Promise<CustomerRow[]> {
  const rows = await get<Array<{ id: string; name: string; phone: string | null; email: string | null }>>(`/api/v1/customers?tenant_id=${tenantId}`)
  // loyalty summary must be fetched separately per customer; backoffice shows basic info
  return rows.map(c => ({ ...c, loyalty_points: 0, tier: '' }))
}

// ── Coupons ───────────────────────────────────────────────────────────────────

export interface CouponRow {
  id: string
  code: string
  name: string
  discount_type: string
  discount_value: string
  valid_from: string | null
  valid_until: string | null
  max_uses: number | null
  used_count: number
  is_active: boolean
}

export interface CouponCreate {
  tenant_id?: string
  code: string
  name: string
  description?: string
  discount_type: string
  discount_value: number
  min_purchase?: number
  valid_from?: string
  valid_until?: string
  max_uses?: number
  per_customer_limit?: number
}

export async function fetchCoupons(): Promise<CouponRow[]> {
  return get<CouponRow[]>('/api/v1/customer-portal/coupons/admin')
}

export async function createCoupon(data: CouponCreate): Promise<CouponRow> {
  return post<CouponRow>('/api/v1/customer-portal/coupons', data)
}

export const CUSTOMER_APP_URL = (import.meta.env.VITE_CUSTOMER_APP_URL as string) || 'http://localhost:5178'
