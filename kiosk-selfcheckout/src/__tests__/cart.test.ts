import { describe, it, expect, beforeEach } from 'vitest'
import { createCart } from '../stores/cart'
import type { Product, Price } from '../types'

function makeProduct(overrides: Partial<Product> = {}): Product {
  return {
    id: 'p1', plu: '001', name: 'Mleko', vat_rate: '9.5',
    unit: 'piece', is_weighable: false, weight_grams: null,
    weight_tolerance_pct: null, age_restricted: false, min_age: null,
    allergens: [], is_active: true, ...overrides,
  }
}

function makePrice(amount = '1.29'): Price {
  return { id: 'pr1', product_id: 'p1', price_type: 'regular', amount, is_active: true }
}

describe('cart store', () => {
  let cart: ReturnType<typeof createCart>

  beforeEach(() => { cart = createCart() })

  it('starts empty', () => {
    expect(cart.lineCount).toBe(0)
    expect(cart.total).toBe(0)
  })

  it('adds a product and computes line total', () => {
    cart.add(makeProduct(), makePrice('2.00'), 3, null, null)
    expect(cart.lineCount).toBe(1)
    expect(cart.lines[0].line_total).toBe(6.00)
    expect(cart.total).toBe(6.00)
  })

  it('merges identical non-weighable products', () => {
    cart.add(makeProduct(), makePrice('1.00'), 2, null, null)
    cart.add(makeProduct(), makePrice('1.00'), 3, null, null)
    expect(cart.lineCount).toBe(1)
    expect(cart.lines[0].qty).toBe(5)
    expect(cart.total).toBe(5.00)
  })

  it('does NOT merge weighable products', () => {
    const wp = makeProduct({ id: 'pw', is_weighable: true })
    cart.add(wp, makePrice('8.00'), 1, 0.5, null)
    cart.add(wp, makePrice('8.00'), 1, 0.3, null)
    expect(cart.lineCount).toBe(2)
  })

  it('computes VAT correctly (inclusive)', () => {
    // 9.5% VAT included in 10€ line total
    cart.add(makeProduct({ vat_rate: '9.5' }), makePrice('10.00'), 1, null, null)
    const line = cart.lines[0]
    const expectedVat = Math.round((10 * 0.095 / 1.095) * 100) / 100
    expect(line.vat_amount).toBeCloseTo(expectedVat, 2)
  })

  it('uses weight_kg as effective qty for weighable items', () => {
    const wp = makeProduct({ id: 'pw', is_weighable: true })
    cart.add(wp, makePrice('5.00'), 1, 1.234, null)
    expect(cart.lines[0].line_total).toBeCloseTo(1.234 * 5.00, 2)
  })

  it('removes a line', () => {
    cart.add(makeProduct(), makePrice('1.00'), 1, null, null)
    cart.removeLine(0)
    expect(cart.lineCount).toBe(0)
  })

  it('clears all lines', () => {
    cart.add(makeProduct(), makePrice('1.00'), 2, null, null)
    cart.add(makeProduct({ id: 'p2', plu: '002' }), makePrice('2.00'), 1, null, null)
    cart.clear()
    expect(cart.lineCount).toBe(0)
    expect(cart.total).toBe(0)
  })

  it('updateQty recomputes line total', () => {
    cart.add(makeProduct(), makePrice('3.00'), 1, null, null)
    cart.updateQty(0, 4)
    expect(cart.lines[0].line_total).toBe(12.00)
  })

  it('sums multiple lines for total', () => {
    cart.add(makeProduct(), makePrice('1.00'), 2, null, null)
    cart.add(makeProduct({ id: 'p2', plu: '002' }), makePrice('3.00'), 1, null, null)
    expect(cart.total).toBe(5.00)
  })
})
