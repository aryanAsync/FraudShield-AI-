import React, { useState } from 'react'
import { AlertCircle, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react'
import { Button } from '../ui/Button'
import { ApiClientError } from '../../api/client'
import './Feedback.css'

interface ErrorStateProps {
  title?: string
  error: Error | ApiClientError | string | null | undefined
  onRetry?: () => void
  className?: string
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Data request failed',
  error,
  onRetry,
  className = '',
}) => {
  const [showDetails, setShowDetails] = useState(false)

  let message = 'An unexpected error occurred while communicating with the service.'
  let status: number | null = null
  let detailsText: string | null = null

  if (typeof error === 'string') {
    message = error
  } else if (error instanceof ApiClientError) {
    message = error.message
    status = error.status
    if (error.details) {
      detailsText = JSON.stringify(error.details, null, 2)
    } else if (error.rawPayload) {
      detailsText = JSON.stringify(error.rawPayload, null, 2)
    }
  } else if (error instanceof Error) {
    message = error.message
  }

  return (
    <div className={`feedback-state error-state ${className}`} role="alert">
      <div className="feedback-icon error-icon" aria-hidden="true">
        <AlertCircle size={32} />
      </div>
      <h3 className="feedback-title">{title}</h3>
      <p className="feedback-desc caption">{message}</p>

      {onRetry && (
        <div className="feedback-action">
          <Button variant="secondary" size="sm" onClick={onRetry} leftIcon={<RefreshCw size={14} />}>
            Retry Request
          </Button>
        </div>
      )}

      {(status || detailsText) && (
        <div className="error-details-container">
          <button
            type="button"
            className="error-toggle-btn caption"
            onClick={() => setShowDetails(!showDetails)}
          >
            <span>{showDetails ? 'Hide technical details' : 'Show technical details'}</span>
            {showDetails ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          {showDetails && (
            <div className="error-details-box mono">
              {status && <div>HTTP Status: {status}</div>}
              {detailsText && <pre>{detailsText}</pre>}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
