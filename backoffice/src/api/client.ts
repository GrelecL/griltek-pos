const BASE = (import.meta.env.VITE_CLOUD_API_URL as string) || 'http://localhost:8000'

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`)
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
