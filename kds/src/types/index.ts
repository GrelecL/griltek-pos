export type KDSStatus = 'in_kitchen' | 'ready' | 'served'

export interface KDSLine {
  id: string
  order_id: string
  product_name: string
  plu: string
  qty: string
  kds_status: KDSStatus
  kds_station: string | null
  course: number | null
  note: string | null
  modifiers: Array<{ group: string; option: string }>
  fired_at: string | null
  ready_at: string | null
}
