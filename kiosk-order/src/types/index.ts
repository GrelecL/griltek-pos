export interface Category {
  id: string
  name: string
  parent_id: string | null
  sort_order: number
}

export interface Product {
  id: string
  plu: string
  name: string
  vat_rate: string
  unit: string
  is_weighable: boolean
  age_restricted: boolean
  min_age: number | null
  allergens: string[]
  modifiers: ModifierGroup[]
  is_active: boolean
  category_id: string | null
}

export interface ModifierGroup {
  name: string
  required: boolean
  multi_select: boolean
  options: ModifierOption[]
}

export interface ModifierOption {
  name: string
  price_delta: string
}

export interface Price {
  product_id: string
  price_type: string
  amount: string
}

export interface CartLine {
  product: Product
  qty: number
  unit_price: number
  line_total: number
  modifiers: SelectedModifier[]
  course: number | null
  note: string
}

export interface SelectedModifier {
  group: string
  option: string
  price_delta: number
}

export type ServiceType = 'eat_in' | 'take_away'
