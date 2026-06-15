export interface Product {
  id: string
  plu: string
  name: string
  vat_rate: string
  unit: string
  is_weighable: boolean
  weight_grams: number | null
  weight_tolerance_pct: string | null
  age_restricted: boolean
  min_age: number | null
  allergens: string[]
  is_active: boolean
}

export interface Price {
  id: string
  product_id: string
  price_type: string
  amount: string
  is_active: boolean
}

export interface CartLine {
  product: Product
  price: Price
  qty: number
  weight_kg: number | null   // null for non-weighable; actual weighed value for weighable
  unit_price: number         // amount per unit (or per kg)
  line_total: number
  vat_rate: number
  vat_amount: number
  security_scale_ok: boolean | null  // null = not checked / not required
}

export type PaymentMethod = 'cash' | 'card' | 'sumup'

export interface SalePayload {
  transaction_uuid: string
  cash_session_id: string | null
  location_id: string
  device_id: string
  lines: SaleLinePayload[]
  payments: SalePaymentPayload[]
}

export interface SaleLinePayload {
  product_id: string
  product_name: string
  plu: string
  qty: number
  unit_price: string
  vat_rate: string
  line_total: string
  vat_amount: string
  discount_pct: string
  discount_amount: string
}

export interface SalePaymentPayload {
  method: PaymentMethod
  amount: string
}
