import { describe, it, expect } from 'vitest'
import type { KDSLine, KDSStatus } from '../types'

// elapsed helper (extracted from App.vue logic for unit testing)
function elapsed(firedAt: string | null): string {
  if (!firedAt) return ''
  const secs = Math.floor((Date.now() - new Date(firedAt).getTime()) / 1000)
  const m = Math.floor(secs / 60)
  const s = secs % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

// board state updater (extracted from WS message handler)
function applyLineUpdate(lines: KDSLine[], updated: KDSLine): KDSLine[] {
  const result = [...lines]
  const idx = result.findIndex(l => l.id === updated.id)
  if (updated.kds_status === 'served') {
    if (idx >= 0) result.splice(idx, 1)
  } else if (idx >= 0) {
    result[idx] = updated
  } else if (updated.kds_status === 'in_kitchen' || updated.kds_status === 'ready') {
    result.push(updated)
  }
  return result
}

function makeLine(id: string, status: KDSStatus, firedAt: string | null = null): KDSLine {
  return {
    id, order_id: 'order-1', product_name: 'Pivo', plu: '500',
    qty: '2', kds_status: status, kds_station: 'bar',
    course: 1, note: null, modifiers: [],
    fired_at: firedAt, ready_at: null,
  }
}

describe('elapsed', () => {
  it('returns empty string for null fired_at', () => {
    expect(elapsed(null)).toBe('')
  })

  it('formats seconds correctly', () => {
    const now = new Date(Date.now() - 75000).toISOString()
    expect(elapsed(now)).toBe('1:15')
  })

  it('pads seconds under 10', () => {
    const now = new Date(Date.now() - 5000).toISOString()
    expect(elapsed(now)).toBe('0:05')
  })
})

describe('applyLineUpdate', () => {
  it('adds a new in_kitchen line', () => {
    const line = makeLine('l1', 'in_kitchen')
    const result = applyLineUpdate([], line)
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe('l1')
  })

  it('updates existing line status to ready', () => {
    const line = makeLine('l1', 'in_kitchen')
    const updated = makeLine('l1', 'ready')
    const result = applyLineUpdate([line], updated)
    expect(result[0].kds_status).toBe('ready')
  })

  it('removes line when served', () => {
    const line = makeLine('l1', 'in_kitchen')
    const served = makeLine('l1', 'served')
    const result = applyLineUpdate([line], served)
    expect(result).toHaveLength(0)
  })

  it('does not add served line that was not on board', () => {
    const served = makeLine('l99', 'served')
    const result = applyLineUpdate([], served)
    expect(result).toHaveLength(0)
  })

  it('preserves other lines when one is updated', () => {
    const l1 = makeLine('l1', 'in_kitchen')
    const l2 = makeLine('l2', 'in_kitchen')
    const updatedL1 = makeLine('l1', 'ready')
    const result = applyLineUpdate([l1, l2], updatedL1)
    expect(result).toHaveLength(2)
    expect(result[0].kds_status).toBe('ready')
    expect(result[1].kds_status).toBe('in_kitchen')
  })
})
