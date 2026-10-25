import type { BatchScoreTransactionItem } from '../../api/types'

export interface CsvValidationResult {
  validItems: BatchScoreTransactionItem[]
  groundTruthClasses: (number | null)[]
  hasGroundTruth: boolean
  errors: { row: number; reason: string }[]
  totalRows: number
  headers: string[]
}

/**
 * Parses and validates CSV content for transaction fraud scoring.
 * Enforces required columns (Time, Amount, V1-V28) and non-negative amounts.
 * Safely extracts ground-truth 'Class' if present without passing it into feature vectors.
 */
export function parseCsvContent(text: string, maxBatchSize: number = 1000): CsvValidationResult {
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0)

  if (lines.length < 2) {
    throw new Error('CSV must contain a header row and at least one data row.')
  }

  const headers = lines[0].split(',').map((h) => h.trim().replace(/^["']|["']$/g, ''))
  const headerLower = headers.map((h) => h.toLowerCase())

  // Check for Time and Amount
  const timeIdx = headerLower.indexOf('time')
  const amountIdx = headerLower.indexOf('amount')

  if (timeIdx === -1) {
    throw new Error("Missing required column 'Time'. Required features: Time, Amount, V1-V28.")
  }
  if (amountIdx === -1) {
    throw new Error("Missing required column 'Amount'. Required features: Time, Amount, V1-V28.")
  }

  // Check for V1 through V28
  const vIndices: Record<string, number> = {}
  for (let i = 1; i <= 28; i++) {
    const vName = `v${i}`
    const idx = headerLower.indexOf(vName)
    if (idx === -1) {
      throw new Error(`Missing required column 'V${i}'. Required features: Time, Amount, V1-V28.`)
    }
    vIndices[`V${i}`] = idx
  }

  // Check for optional Class column (ground-truth label)
  const classIdx = headerLower.indexOf('class')
  const hasGroundTruth = classIdx !== -1

  const validItems: BatchScoreTransactionItem[] = []
  const groundTruthClasses: (number | null)[] = []
  const errors: { row: number; reason: string }[] = []

  const maxRows = Math.min(lines.length - 1, maxBatchSize)

  for (let lineNum = 1; lineNum <= maxRows; lineNum++) {
    const rowLine = lines[lineNum]
    const cols = rowLine.split(',').map((c) => c.trim().replace(/^["']|["']$/g, ''))

    if (cols.length < headers.length) {
      errors.push({
        row: lineNum,
        reason: `Row has ${cols.length} values, expected ${headers.length} columns`,
      })
      continue
    }

    const timeVal = parseFloat(cols[timeIdx])
    if (isNaN(timeVal) || !isFinite(timeVal)) {
      errors.push({ row: lineNum, reason: `Invalid Time value: '${cols[timeIdx]}'` })
      continue
    }

    const amountVal = parseFloat(cols[amountIdx])
    if (isNaN(amountVal) || !isFinite(amountVal) || amountVal < 0) {
      errors.push({ row: lineNum, reason: `Invalid Amount (must be >= 0): '${cols[amountIdx]}'` })
      continue
    }

    const item: any = {
      Time: timeVal,
      Amount: amountVal,
    }

    let vFailed = false
    for (let i = 1; i <= 28; i++) {
      const vKey = `V${i}`
      const vVal = parseFloat(cols[vIndices[vKey]])
      if (isNaN(vVal) || !isFinite(vVal)) {
        errors.push({ row: lineNum, reason: `Invalid numeric value for ${vKey}: '${cols[vIndices[vKey]]}'` })
        vFailed = true
        break
      }
      item[vKey] = vVal
    }

    if (vFailed) continue

    validItems.push(item as BatchScoreTransactionItem)

    if (hasGroundTruth) {
      const gt = parseInt(cols[classIdx], 10)
      groundTruthClasses.push(isNaN(gt) ? null : gt)
    }
  }

  return {
    validItems,
    groundTruthClasses,
    hasGroundTruth,
    errors,
    totalRows: lines.length - 1,
    headers,
  }
}
