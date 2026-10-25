import React from 'react'
import { formatProbability } from '../../lib/format'
import './ProbabilityMeter.css'

interface ProbabilityMeterProps {
  probability: number | null | undefined
  threshold?: number | null
  showMeter?: boolean
  size?: 'sm' | 'md' | 'lg'
}

export const ProbabilityMeter: React.FC<ProbabilityMeterProps> = ({
  probability,
  threshold,
  showMeter = true,
  size = 'md',
}) => {
  const { percent, raw } = formatProbability(probability)
  const val = Math.min(Math.max(probability ?? 0, 0), 1) * 100
  const threshVal = threshold !== null && threshold !== undefined ? threshold * 100 : null

  return (
    <div className={`probability-display size-${size}`} title={`Raw model output: ${raw}`}>
      <div className="probability-value-row">
        <span className="probability-num mono">{percent}</span>
        {threshold !== null && threshold !== undefined && (
          <span className="threshold-caption caption">
            (thr: {(threshold * 100).toFixed(0)}%)
          </span>
        )}
      </div>

      {showMeter && (
        <div className="probability-track" aria-hidden="true">
          <div className="probability-fill" style={{ width: `${val}%` }} />
          {threshVal !== null && (
            <div
              className="threshold-tick"
              style={{ left: `${threshVal}%` }}
              title={`Decision threshold: ${(threshold! * 100).toFixed(1)}%`}
            />
          )}
        </div>
      )}
    </div>
  )
}
