import { describe, it, expect } from 'vitest'
import { parseCsvContent } from '../csvParser'

describe('parseCsvContent', () => {
  const buildValidHeader = (includeClass = false) => {
    const vCols = Array.from({ length: 28 }, (_, i) => `V${i + 1}`).join(',')
    return includeClass ? `Time,Amount,${vCols},Class` : `Time,Amount,${vCols}`
  }

  const buildValidRow = (time = 100.0, amount = 25.5, classVal?: number) => {
    const vVals = Array.from({ length: 28 }, (_, i) => (0.1 * (i + 1)).toFixed(3)).join(',')
    return classVal !== undefined ? `${time},${amount},${vVals},${classVal}` : `${time},${amount},${vVals}`
  }

  it('parses valid CSV without ground-truth Class column', () => {
    const csv = `${buildValidHeader(false)}\n${buildValidRow(10.0, 50.0)}\n${buildValidRow(20.0, 150.0)}`
    const result = parseCsvContent(csv)

    expect(result.totalRows).toBe(2)
    expect(result.validItems.length).toBe(2)
    expect(result.hasGroundTruth).toBe(false)
    expect(result.validItems[0].Time).toBe(10.0)
    expect(result.validItems[0].Amount).toBe(50.0)
    expect(result.validItems[0].V1).toBe(0.1)
    expect(result.validItems[0].V28).toBe(2.8)
    // Extra fields like Class must not be attached to validItems
    expect((result.validItems[0] as any).Class).toBeUndefined()
  })

  it('detects and isolates ground-truth Class column without passing it to feature vector', () => {
    const csv = `${buildValidHeader(true)}\n${buildValidRow(12.0, 99.99, 1)}\n${buildValidRow(15.0, 5.0, 0)}`
    const result = parseCsvContent(csv)

    expect(result.hasGroundTruth).toBe(true)
    expect(result.validItems.length).toBe(2)
    expect(result.groundTruthClasses).toEqual([1, 0])
    // Ground truth is isolated and never passed into model feature vector
    expect((result.validItems[0] as any).Class).toBeUndefined()
    expect((result.validItems[1] as any).Class).toBeUndefined()
  })

  it('throws error when required columns are missing', () => {
    const missingTime = 'Amount,V1,V2\n10.0,0.1,0.2'
    expect(() => parseCsvContent(missingTime)).toThrow(/Missing required column 'Time'/)

    const missingV28 = `Time,Amount,${Array.from({ length: 27 }, (_, i) => `V${i + 1}`).join(',')}\n0,10,...`
    expect(() => parseCsvContent(missingV28)).toThrow(/Missing required column 'V28'/)
  })

  it('identifies and skips malformed rows with negative amount or invalid numbers', () => {
    const csv = `${buildValidHeader(false)}\n${buildValidRow(10.0, -5.0)}\n${buildValidRow(20.0, 30.0)}`
    const result = parseCsvContent(csv)

    expect(result.totalRows).toBe(2)
    expect(result.validItems.length).toBe(1)
    expect(result.errors.length).toBe(1)
    expect(result.errors[0].row).toBe(1)
    expect(result.errors[0].reason).toContain('Amount (must be >= 0)')
  })
})
