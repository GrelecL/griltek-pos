import { reactive, computed } from 'vue'
import type { CartLine, Product, SelectedModifier } from '../types'

export interface OrderCart {
  lines: CartLine[]
  serviceType: 'eat_in' | 'take_away'
  pagerNumber: string
  add(product: Product, unitPrice: number, modifiers: SelectedModifier[], course: number | null): void
  updateQty(index: number, qty: number): void
  removeLine(index: number): void
  clear(): void
  total: number
  lineCount: number
}

function buildLine(product: Product, unitPrice: number, modifiers: SelectedModifier[], course: number | null): CartLine {
  const modifierDelta = modifiers.reduce((s, m) => s + m.price_delta, 0)
  const effectivePrice = unitPrice + modifierDelta
  return {
    product,
    qty: 1,
    unit_price: effectivePrice,
    line_total: Math.round(effectivePrice * 100) / 100,
    modifiers,
    course,
    note: '',
  }
}

function recompute(line: CartLine): void {
  line.line_total = Math.round(line.unit_price * line.qty * 100) / 100
}

export function createOrderCart(): OrderCart {
  const lines = reactive<CartLine[]>([])
  const serviceType = reactive({ value: 'eat_in' as 'eat_in' | 'take_away' })
  const pagerNumber = reactive({ value: '' })

  const total = computed(() => lines.reduce((s, l) => s + l.line_total, 0))
  const lineCount = computed(() => lines.length)

  return {
    lines,
    get serviceType() { return serviceType.value },
    set serviceType(v: 'eat_in' | 'take_away') { serviceType.value = v },
    get pagerNumber() { return pagerNumber.value },
    set pagerNumber(v: string) { pagerNumber.value = v },
    add(product, unitPrice, modifiers, course) {
      // Merge identical products with no modifiers
      if (modifiers.length === 0 && course === null) {
        const existing = lines.find(l => l.product.id === product.id && l.modifiers.length === 0)
        if (existing) {
          existing.qty += 1
          recompute(existing)
          return
        }
      }
      lines.push(buildLine(product, unitPrice, modifiers, course))
    },
    updateQty(index, qty) {
      const line = lines[index]
      if (!line) return
      line.qty = qty
      recompute(line)
    },
    removeLine(index) {
      lines.splice(index, 1)
    },
    clear() {
      lines.splice(0)
      serviceType.value = 'eat_in'
      pagerNumber.value = ''
    },
    get total() { return total.value },
    get lineCount() { return lineCount.value },
  }
}
