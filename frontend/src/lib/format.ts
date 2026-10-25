/**
 * Formatting utilities for timestamps, numeric amounts, and probabilities.
 * Adheres to FraudShield AI design guidelines:
 * - No fabricated currency symbols (amount is plain numeric units).
 * - Exact precision representations.
 * - Timezone transparency.
 */

export function formatTimestamp(
  isoDateStr: string | null | undefined,
  options?: { includeTime?: boolean; includeSeconds?: boolean }
): { display: string; iso: string } {
  if (!isoDateStr) {
    return { display: '—', iso: '' }
  }

  try {
    const d = new Date(isoDateStr)
    if (isNaN(d.getTime())) {
      return { display: isoDateStr, iso: isoDateStr }
    }

    const { includeTime = true, includeSeconds = true } = options || {}

    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')

    let display = `${year}-${month}-${day}`

    if (includeTime) {
      const hours = String(d.getHours()).padStart(2, '0')
      const minutes = String(d.getMinutes()).padStart(2, '0')
      let timeStr = `${hours}:${minutes}`
      if (includeSeconds) {
        const seconds = String(d.getSeconds()).padStart(2, '0')
        timeStr += `:${seconds}`
      }

      // Local timezone name/abbreviation
      const tzMatch = d.toLocaleTimeString('en-US', { timeZoneName: 'short' }).split(' ')
      const tzAbbrev = tzMatch[tzMatch.length - 1] || 'Local'

      display += ` ${timeStr} ${tzAbbrev}`
    }

    return { display, iso: d.toISOString() }
  } catch {
    return { display: isoDateStr, iso: isoDateStr }
  }
}

export function formatAmount(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) {
    return '0.00'
  }
  return value.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

export function formatProbability(value: number | null | undefined): {
  percent: string
  raw: string
} {
  if (value === null || value === undefined || isNaN(value)) {
    return { percent: '0.00%', raw: '0.0' }
  }
  const pct = (value * 100).toFixed(2) + '%'
  return { percent: pct, raw: value.toString() }
}

export function formatRiskScore(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) {
    return '0.0'
  }
  return value.toFixed(1)
}

export function formatSeconds(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || isNaN(seconds)) {
    return '—'
  }
  if (seconds < 60) {
    return `${Math.round(seconds)}s`
  }
  if (seconds < 3600) {
    return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
  }
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.round((seconds % 3600) / 60)
  return `${hrs}h ${mins}m`
}
