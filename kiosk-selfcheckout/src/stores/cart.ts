import { reactive, computed } from 'vue'
import type { CartLine, Product, Price } from '../types'

export interface CartStore {
  lines: CartLine[]
  add(product: Product, price: Price, qty: number, weight_kg: number | null, security_scale_ok: boolean | null): void
  updateQty(index: number, qty: number): void
  removeLine(index: number): void
  clear(): void
  subtotal: number
  vatTotal: number
  total: number
  lineCount: number
}

function buildLine(
  product: Product,
  price: Price,
  qty: number,
  weight_kg: number | null,
  security_scale_ok: boolean | null,
): CartLine {
  const unitPrice = parseFloat(price.amount)
  const vatRate = parseFloat(product.vat_rate) / 100
  const effectiveQty = weight_kg !== null ? weight_kg : qty
  const lineTotal = Math.round(unitPrice * effectiveQty * 100) / 100
  const vatAmount = Math.round((lineTotal * vatRate) / (1 + vatRate) * 100) / 100
  return { product, price, qty, weight_kg, unit_price: unitPrice, line_total: lineTotal, vat_rate: parseFloat(product.vat_rate), vat_amount: vatAmount, security_scale_ok }
}

function recompute(line: CartLine): CartLine {
  return buildLine(line.product, line.price, line.qty, line.weight_kg, line.security_scale_ok)
}

export function createCart(): CartStore {
  const lines = reactive<CartLine[]>([])

  const subtotal = computed(() => lines.reduce((s, l) => s + l.line_total, 0))
  const vatTotal = computed(() => lines.reduce((s, l) => s + l.vat_amount, 0))
  const total = computed(() => subtotal.value)
  const lineCount = computed(() => lines.length)

  return {
    lines,
    add(product, price, qty, weight_kg, security_scale_ok) {
      // Merge identical non-weighable products
      if (!product.is_weighable) {
        const existing = lines.find(l => l.product.id === product.id)
        if (existing) {
          existing.qty += qty
          Object.assign(existing, recompute(existing))
          return
        }
      }
      lines.push(buildLine(product, price, qty, weight_kg, security_scale_ok))
    },
    updateQty(index, qty) {
      const line = lines[index]
      if (!line) return
      line.qty = qty
      Object.assign(line, recompute(line))
    },
    removeLine(index) {
      lines.splice(index, 1)
    },
    clear() {
      lines.splice(0)
    },
    get subtotal() { return subtotal.value },
    get vatTotal() { return vatTotal.value },
    get total() { return total.value },
    get lineCount() { return lineCount.value },
  }
}
