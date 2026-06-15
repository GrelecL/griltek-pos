import { describe, it, expect, beforeEach } from 'vitest'
import { createOrderCart } from '../stores/orderCart'
import type { Product } from '../types'

function makeProduct(overrides: Partial<Product> = {}): Product {
  return {
    id: 'p1', plu: '001', name: 'Pivo', vat_rate: '9.5', unit: 'piece',
    is_weighable: false, age_restricted: false, min_age: null,
    allergens: [], modifiers: [], is_active: true, category_id: null,
    ...overrides,
  }
}

describe('orderCart', () => {
  let cart: ReturnType<typeof createOrderCart>

  beforeEach(() => { cart = createOrderCart() })

  it('starts empty', () => {
    expect(cart.lineCount).toBe(0)
    expect(cart.total).toBe(0)
  })

  it('adds a product', () => {
    cart.add(makeProduct(), 3.50, [], null)
    expect(cart.lineCount).toBe(1)
    expect(cart.lines[0].line_total).toBe(3.50)
  })

  it('merges identical products without modifiers', () => {
    cart.add(makeProduct(), 3.50, [], null)
    cart.add(makeProduct(), 3.50, [], null)
    expect(cart.lineCount).toBe(1)
    expect(cart.lines[0].qty).toBe(2)
    expect(cart.lines[0].line_total).toBe(7.00)
  })

  it('does NOT merge products with modifiers', () => {
    const mod = [{ group: 'Velikost', option: 'Malo', price_delta: 0 }]
    cart.add(makeProduct(), 3.50, mod, null)
    cart.add(makeProduct(), 3.50, mod, null)
    expect(cart.lineCount).toBe(2)
  })

  it('adds modifier price delta to unit price', () => {
    const mods = [{ group: 'Extra', option: 'Sir', price_delta: 0.50 }]
    cart.add(makeProduct(), 3.50, mods, null)
    expect(cart.lines[0].unit_price).toBe(4.00)
    expect(cart.lines[0].line_total).toBe(4.00)
  })

  it('removes a line', () => {
    cart.add(makeProduct(), 2.00, [], null)
    cart.removeLine(0)
    expect(cart.lineCount).toBe(0)
  })

  it('clears and resets service type', () => {
    cart.add(makeProduct(), 2.00, [], null)
    cart.serviceType = 'take_away'
    cart.clear()
    expect(cart.lineCount).toBe(0)
    expect(cart.serviceType).toBe('eat_in')
  })

  it('sums multiple lines', () => {
    cart.add(makeProduct(), 2.00, [], null)
    cart.add(makeProduct({ id: 'p2' }), 3.00, [], null)
    expect(cart.total).toBe(5.00)
  })

  it('negative modifier delta reduces price', () => {
    const mods = [{ group: 'Size', option: 'Small', price_delta: -1.00 }]
    cart.add(makeProduct(), 5.00, mods, null)
    expect(cart.lines[0].unit_price).toBe(4.00)
  })
})
