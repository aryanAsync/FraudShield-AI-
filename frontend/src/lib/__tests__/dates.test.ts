import { describe, it, expect } from 'vitest'
import { computeDateRange } from '../dates'

describe('computeDateRange', () => {
  it('returns undefined start and end for preset "all"', () => {
    const range = computeDateRange('all')
    expect(range.start_date).toBeUndefined()
    expect(range.end_date).toBeUndefined()
  })

  it('computes 7d range correctly', () => {
    const range = computeDateRange('7d')
    expect(range.start_date).toBeDefined()
    expect(range.end_date).toBeDefined()
    const start = new Date(range.start_date!)
    const end = new Date(range.end_date!)
    const diffDays = Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
    expect(diffDays).toBe(7)
  })

  it('computes 30d range correctly', () => {
    const range = computeDateRange('30d')
    const start = new Date(range.start_date!)
    const end = new Date(range.end_date!)
    const diffDays = Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
    expect(diffDays).toBe(30)
  })

  it('computes 90d range correctly', () => {
    const range = computeDateRange('90d')
    const start = new Date(range.start_date!)
    const end = new Date(range.end_date!)
    const diffDays = Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
    expect(diffDays).toBe(90)
  })
})
