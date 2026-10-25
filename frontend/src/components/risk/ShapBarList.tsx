import React from 'react'
import type { FeatureAttribution } from '../../api/types'
import { SHAP_DISCLAIMER } from '../../lib/constants'
import { Info } from 'lucide-react'
import './ShapBarList.css'

interface ShapBarListProps {
  explanations: FeatureAttribution[] | null | undefined
  className?: string
  disclaimer?: string
}

export const ShapBarList: React.FC<ShapBarListProps> = ({
  explanations,
  className = '',
  disclaimer = SHAP_DISCLAIMER,
}) => {
  if (!explanations || explanations.length === 0) {
    return (
      <div className={`shap-empty-state ${className}`}>
        <p className="caption">No feature attribution explanation available for this prediction.</p>
      </div>
    )
  }

  // Find max absolute attribution for relative bar width
  const maxAbs = Math.max(...explanations.map((e) => Math.abs(e.attribution)), 0.001)

  return (
    <div className={`shap-container ${className}`}>
      <div className="shap-header">
        <h4 className="shap-title">Model Input Feature Contributions (SHAP)</h4>
        <span className="caption">Relative push toward (+) or away (-) from model fraud classification</span>
      </div>

      <div className="shap-list" role="list">
        {explanations.map((item, idx) => {
          const isPositive = item.attribution >= 0
          const pctWidth = Math.min((Math.abs(item.attribution) / maxAbs) * 100, 100)

          return (
            <div key={`${item.feature}-${idx}`} className="shap-row" role="listitem">
              <div className="shap-feature-label">
                <span className="mono feature-name">{item.feature}</span>
                <span className="caption mono feature-val">val: {item.value.toFixed(3)}</span>
              </div>

              <div className="shap-bar-track">
                {/* Center zero line */}
                <div className="shap-zero-line" />

                {/* Left side: negative attribution */}
                <div className="shap-side shap-left">
                  {!isPositive && (
                    <div
                      className="shap-bar shap-bar-negative"
                      style={{ width: `${pctWidth}%` }}
                      title={`Contribution: ${item.attribution.toFixed(4)}`}
                    />
                  )}
                </div>

                {/* Right side: positive attribution */}
                <div className="shap-side shap-right">
                  {isPositive && (
                    <div
                      className="shap-bar shap-bar-positive"
                      style={{ width: `${pctWidth}%` }}
                      title={`Contribution: +${item.attribution.toFixed(4)}`}
                    />
                  )}
                </div>
              </div>

              <div className="shap-value mono">
                {isPositive ? `+${item.attribution.toFixed(4)}` : item.attribution.toFixed(4)}
              </div>
            </div>
          )
        })}
      </div>

      <div className="shap-disclaimer">
        <Info size={14} className="shap-disclaimer-icon" />
        <p className="caption">{disclaimer}</p>
      </div>
    </div>
  )
}
