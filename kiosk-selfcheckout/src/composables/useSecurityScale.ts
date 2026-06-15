/**
 * Security scale check: compare expected weight (weight_grams × qty) against
 * measured tray weight. Flag if deviation exceeds tolerance.
 */
export interface ScaleCheckResult {
  passed: boolean
  expected_g: number
  measured_g: number
  deviation_pct: number
}

export function checkSecurityScale(
  weight_grams: number,
  qty: number,
  measured_g: number,
  tolerance_pct: number,
): ScaleCheckResult {
  const expected_g = weight_grams * qty
  const deviation_pct = expected_g === 0
    ? 0
    : Math.abs(measured_g - expected_g) / expected_g * 100
  return {
    passed: deviation_pct <= tolerance_pct,
    expected_g,
    measured_g,
    deviation_pct,
  }
}
