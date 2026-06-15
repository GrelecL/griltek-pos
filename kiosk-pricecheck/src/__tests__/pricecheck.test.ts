import { describe, it, expect } from 'vitest'

describe('price formatting', () => {
  function formatPrice(amount: string): string {
    return parseFloat(amount).toFixed(2)
  }

  it('formats integer prices', () => {
    expect(formatPrice('2')).toBe('2.00')
  })

  it('formats decimal prices', () => {
    expect(formatPrice('3.5')).toBe('3.50')
  })

  it('rounds to 2 decimals', () => {
    expect(formatPrice('1.999')).toBe('2.00')
  })
})

describe('barcode buffer', () => {
  let buf = ''
  const results: string[] = []

  function key(k: string) {
    if (k === 'Enter') {
      const code = buf.trim()
      buf = ''
      if (code.length >= 3) results.push(code)
    } else if (k.length === 1) {
      buf += k
    }
  }

  it('emits code on Enter', () => {
    buf = ''; results.splice(0)
    '12345678'.split('').forEach(k => key(k))
    key('Enter')
    expect(results).toEqual(['12345678'])
  })

  it('ignores short sequences', () => {
    buf = ''; results.splice(0)
    'AB'.split('').forEach(k => key(k))
    key('Enter')
    expect(results).toHaveLength(0)
  })
})
