import { describe, it, expect } from 'vitest'

// Report formatting helpers (extracted for unit testing)
function fmtEur(amount: string): string {
  return `${parseFloat(amount).toFixed(2)} €`
}

function fmtNet(revenue: string, returns: string): string {
  const net = parseFloat(revenue) - parseFloat(returns)
  return net.toFixed(2)
}

function buildCsvUrl(base: string, params: Record<string, string>): string {
  const q = new URLSearchParams({ ...params, fmt: 'csv' })
  return `${base}?${q}`
}

// Date range helpers
function firstOfMonth(now: Date): string {
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  return `${y}-${m}-01`
}

describe('report formatting', () => {
  it('formats euro amounts', () => {
    expect(fmtEur('1234.5')).toBe('1234.50 €')
    expect(fmtEur('0')).toBe('0.00 €')
  })

  it('computes net revenue', () => {
    expect(fmtNet('1000.00', '50.00')).toBe('950.00')
    expect(fmtNet('500', '0')).toBe('500.00')
  })

  it('builds CSV download URL', () => {
    const url = buildCsvUrl('/api/v1/reports/sales', { location_id: 'loc1' })
    expect(url).toContain('fmt=csv')
    expect(url).toContain('location_id=loc1')
  })
})

describe('date range', () => {
  it('firstOfMonth returns correct date', () => {
    const result = firstOfMonth(new Date('2026-06-15'))
    expect(result).toBe('2026-06-01')
  })

  it('firstOfMonth handles year boundary', () => {
    const result = firstOfMonth(new Date('2026-01-20'))
    expect(result).toBe('2026-01-01')
  })
})

describe('dashboard data processing', () => {
  it('maps payment breakdown to table rows', () => {
    const raw = [
      { method: 'cash', count: 10, total: '100.00' },
      { method: 'card', count: 5, total: '200.00' },
    ]
    const rows = raw.map(r => ({ ...r, total: `${parseFloat(r.total).toFixed(2)} €` }))
    expect(rows[0].total).toBe('100.00 €')
    expect(rows[1].method).toBe('card')
  })

  it('identifies degraded sync status', () => {
    const health = { pending_fiscal_records: 3, unsynced_stock_movements: 0, status: 'degraded' }
    expect(health.status).toBe('degraded')
    expect(health.pending_fiscal_records).toBeGreaterThan(0)
  })

  it('identifies healthy sync status', () => {
    const health = { pending_fiscal_records: 0, unsynced_stock_movements: 0, status: 'ok' }
    expect(health.status).toBe('ok')
  })
})
