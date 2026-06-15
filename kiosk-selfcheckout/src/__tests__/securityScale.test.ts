import { describe, it, expect } from 'vitest'
import { checkSecurityScale } from '../composables/useSecurityScale'

describe('checkSecurityScale', () => {
  it('passes when measured weight equals expected', () => {
    const result = checkSecurityScale(200, 3, 600, 5)
    expect(result.passed).toBe(true)
    expect(result.expected_g).toBe(600)
    expect(result.deviation_pct).toBe(0)
  })

  it('passes when deviation is within tolerance', () => {
    // expected 600g, measured 615g → 2.5% deviation, tolerance 5%
    const result = checkSecurityScale(200, 3, 615, 5)
    expect(result.passed).toBe(true)
    expect(result.deviation_pct).toBeCloseTo(2.5, 1)
  })

  it('fails when deviation exceeds tolerance', () => {
    // expected 600g, measured 700g → 16.7% deviation, tolerance 5%
    const result = checkSecurityScale(200, 3, 700, 5)
    expect(result.passed).toBe(false)
    expect(result.deviation_pct).toBeCloseTo(16.67, 1)
  })

  it('handles zero expected weight without division error', () => {
    const result = checkSecurityScale(0, 1, 0, 5)
    expect(result.passed).toBe(true)
    expect(result.deviation_pct).toBe(0)
  })

  it('catches missing item (expected weight, measured 0)', () => {
    const result = checkSecurityScale(500, 1, 0, 5)
    expect(result.passed).toBe(false)
    expect(result.deviation_pct).toBeCloseTo(100, 0)
  })

  it('works with fractional tolerance', () => {
    // expected 1000g, measured 1002g → 0.2% deviation, tolerance 0.5%
    const result = checkSecurityScale(1000, 1, 1002, 0.5)
    expect(result.passed).toBe(true)
  })

  it('reports measured_g in result', () => {
    const result = checkSecurityScale(100, 2, 195, 10)
    expect(result.measured_g).toBe(195)
    expect(result.expected_g).toBe(200)
  })
})
