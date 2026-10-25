/**
 * Date range helpers for telemetry and analytics
 */

export function computeDateRange(preset: '7d' | '30d' | '90d' | 'all'): {
  start_date?: string
  end_date?: string
} {
  if (preset === 'all') {
    return { start_date: undefined, end_date: undefined }
  }
  const end = new Date()
  const start = new Date()
  if (preset === '7d') {
    start.setDate(end.getDate() - 7)
  } else if (preset === '30d') {
    start.setDate(end.getDate() - 30)
  } else if (preset === '90d') {
    start.setDate(end.getDate() - 90)
  }
  return {
    start_date: start.toISOString(),
    end_date: end.toISOString(),
  }
}
