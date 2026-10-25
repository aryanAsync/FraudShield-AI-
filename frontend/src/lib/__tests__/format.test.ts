import { describe, it, expect } from 'vitest'
import {
  formatAmount,
  formatProbability,
  formatRiskScore,
  formatSeconds,
  formatTimestamp,
} from '../format'

describe('Format Utilities', () => {
  describe('formatAmount', () => {
    it('formats plain numeric units with 2 decimals without fabricated currency symbols', () => {
      expect(formatAmount(149.5)).toBe('149.50')
      expect(formatAmount(1000)).toBe('1,000.00')
      expect(formatAmount(0)).toBe('0.00')
      expect(formatAmount(null)).toBe('0.00')
      expect(formatAmount(undefined)).toBe('0.00')
    })

    it('handles negative amounts and precision', () => {
      expect(formatAmount(-25.75)).toBe('-25.75')
      expect(formatAmount(12.3456)).toBe('12.35')
    })
  })

  describe('formatProbability', () => {
    it('returns both percentage string and raw probability representation', () => {
      const res = formatProbability(0.8523)
      expect(res.percent).toBe('85.23%')
      expect(res.raw).toBe('0.8523')

      const zero = formatProbability(0)
      expect(zero.percent).toBe('0.00%')
      expect(zero.raw).toBe('0')

      const nil = formatProbability(null)
      expect(nil.percent).toBe('0.00%')
      expect(nil.raw).toBe('0.0')
    })
  })

  describe('formatRiskScore', () => {
    it('formats risk scores to 1 decimal place', () => {
      expect(formatRiskScore(75.42)).toBe('75.4')
      expect(formatRiskScore(100)).toBe('100.0')
      expect(formatRiskScore(0)).toBe('0.0')
      expect(formatRiskScore(null)).toBe('0.0')
    })
  })

  describe('formatSeconds', () => {
    it('formats zero or undefined duration', () => {
      expect(formatSeconds(null)).toBe('—')
      expect(formatSeconds(undefined)).toBe('—')
      expect(formatSeconds(0)).toBe('0s')
    })

    it('formats duration in seconds', () => {
      expect(formatSeconds(45)).toBe('45s')
    })

    it('formats duration in minutes and seconds', () => {
      expect(formatSeconds(150)).toBe('2m 30s')
      expect(formatSeconds(120)).toBe('2m 0s')
    })

    it('formats duration in hours and minutes', () => {
      expect(formatSeconds(3600)).toBe('1h 0m')
      expect(formatSeconds(3665)).toBe('1h 1m')
    })
  })

  describe('formatTimestamp', () => {
    it('handles null and undefined timestamps gracefully', () => {
      const res = formatTimestamp(null)
      expect(res.display).toBe('—')
      expect(res.iso).toBe('')
    })

    it('formats valid ISO timestamps with timezone-aware display and full ISO string', () => {
      const res = formatTimestamp('2026-10-25T12:30:00Z')
      expect(res.iso).toBe('2026-10-25T12:30:00.000Z')
      expect(res.display).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}/)
    })
  })
})
