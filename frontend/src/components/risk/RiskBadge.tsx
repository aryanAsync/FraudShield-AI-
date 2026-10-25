import React from 'react'
import type { RiskLevel } from '../../api/types'
import './RiskBadge.css'

interface RiskBadgeProps {
  level: RiskLevel | string | null | undefined
  size?: 'sm' | 'md'
  className?: string
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level, size = 'md', className = '' }) => {
  const normalized = (level || '').toUpperCase()

  let tierClass = 'risk-unknown'
  let glyph = '—'
  let label = 'Unrated'

  if (normalized === 'LOW') {
    tierClass = 'risk-low'
    glyph = '●'
    label = 'Low'
  } else if (normalized === 'MEDIUM') {
    tierClass = 'risk-med'
    glyph = '▲'
    label = 'Medium'
  } else if (normalized === 'HIGH') {
    tierClass = 'risk-high'
    glyph = '◆'
    label = 'High'
  }

  return (
    <span
      className={`risk-badge ${tierClass} risk-badge-${size} ${className}`}
      aria-label={`Risk tier: ${label}`}
    >
      <span className="risk-badge-glyph" aria-hidden="true">
        {glyph}
      </span>
      <span className="risk-badge-label">{label}</span>
    </span>
  )
}
