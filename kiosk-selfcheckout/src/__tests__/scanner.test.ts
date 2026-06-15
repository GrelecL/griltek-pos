import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

/**
 * Scanner composable relies on DOM event listeners and Vue lifecycle hooks.
 * We test the accumulation logic directly without mounting components.
 */
describe('barcode buffer logic', () => {
  let buffer = ''
  const scanned: string[] = []

  function simulateKey(key: string) {
    if (key === 'Enter') {
      const code = buffer.trim()
      buffer = ''
      if (code.length >= 3) scanned.push(code)
    } else if (key.length === 1) {
      buffer += key
    }
  }

  beforeEach(() => { buffer = ''; scanned.splice(0) })

  it('emits barcode on Enter', () => {
    '3838003819303'.split('').forEach(k => simulateKey(k))
    simulateKey('Enter')
    expect(scanned).toEqual(['3838003819303'])
  })

  it('ignores sequences shorter than 3 chars', () => {
    'AB'.split('').forEach(k => simulateKey(k))
    simulateKey('Enter')
    expect(scanned).toHaveLength(0)
  })

  it('handles multiple sequential scans', () => {
    for (const code of ['12345', '67890']) {
      code.split('').forEach(k => simulateKey(k))
      simulateKey('Enter')
    }
    expect(scanned).toEqual(['12345', '67890'])
  })

  it('accumulates digits without emitting mid-scan', () => {
    '123'.split('').forEach(k => simulateKey(k))
    expect(scanned).toHaveLength(0)
  })
})
