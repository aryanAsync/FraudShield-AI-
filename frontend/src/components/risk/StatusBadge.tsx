import React from 'react'
import type { CaseStatus } from '../../api/types'
import './StatusBadge.css'

interface StatusBadgeProps {
  status: CaseStatus | string | null | undefined
  size?: 'sm' | 'md'
  className?: string
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
  className = '',
}) => {
  const norm = (status || '').toUpperCase()

  let statusClass = 'status-unknown'
  let glyph = '○'
  let label = status || 'Unknown'

  switch (norm) {
    case 'OPEN':
      statusClass = 'status-open'
      glyph = '○'
      label = 'Open'
      break
    case 'IN_REVIEW':
      statusClass = 'status-review'
      glyph = '◐'
      label = 'In review'
      break
    case 'CONFIRMED_FRAUD':
      statusClass = 'status-fraud'
      glyph = '🛡'
      label = 'Confirmed fraud'
      break
    case 'LEGITIMATE':
      statusClass = 'status-legit'
      glyph = '✓'
      label = 'Legitimate'
      break
    case 'CLOSED':
      statusClass = 'status-closed'
      glyph = '🔒'
      label = 'Closed'
      break
  }

  return (
    <span
      className={`status-badge ${statusClass} status-badge-${size} ${className}`}
      aria-label={`Case status: ${label}`}
    >
      <span className="status-badge-glyph" aria-hidden="true">
        {glyph}
      </span>
      <span className="status-badge-label">{label}</span>
    </span>
  )
}
