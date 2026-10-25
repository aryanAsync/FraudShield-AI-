import React, { forwardRef, useId } from 'react'
import { AlertCircle } from 'lucide-react'
import './Input.css'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  helperText?: string
  error?: string
  leftAddon?: React.ReactNode
  rightAddon?: React.ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, helperText, error, leftAddon, rightAddon, id, className = '', ...props }, ref) => {
    const generatedId = useId()
    const inputId = id || generatedId
    const helperId = `${inputId}-helper`
    const errorId = `${inputId}-error`

    const describedBy = error ? errorId : helperText ? helperId : undefined

    return (
      <div className={`input-field-group ${error ? 'has-error' : ''} ${className}`}>
        {label && (
          <label htmlFor={inputId} className="input-label">
            {label}
          </label>
        )}
        <div className="input-wrapper">
          {leftAddon && <span className="input-addon input-addon-left">{leftAddon}</span>}
          <input
            ref={ref}
            id={inputId}
            aria-invalid={!!error}
            aria-describedby={describedBy}
            className="input-control"
            {...props}
          />
          {rightAddon && <span className="input-addon input-addon-right">{rightAddon}</span>}
        </div>
        {error && (
          <p id={errorId} className="input-message input-error" role="alert">
            <AlertCircle size={14} />
            <span>{error}</span>
          </p>
        )}
        {!error && helperText && (
          <p id={helperId} className="input-message input-helper">
            {helperText}
          </p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'
