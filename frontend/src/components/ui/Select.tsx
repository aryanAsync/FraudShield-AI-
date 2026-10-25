import React, { forwardRef, useId } from 'react'
import { AlertCircle, ChevronDown } from 'lucide-react'
import './Input.css'
import './Select.css'

export interface SelectOption {
  value: string | number
  label: string
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  helperText?: string
  error?: string
  options?: SelectOption[]
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, helperText, error, options, children, id, className = '', ...props }, ref) => {
    const generatedId = useId()
    const selectId = id || generatedId
    const helperId = `${selectId}-helper`
    const errorId = `${selectId}-error`

    const describedBy = error ? errorId : helperText ? helperId : undefined

    return (
      <div className={`input-field-group ${error ? 'has-error' : ''} ${className}`}>
        {label && (
          <label htmlFor={selectId} className="input-label">
            {label}
          </label>
        )}
        <div className="select-wrapper">
          <select
            ref={ref}
            id={selectId}
            aria-invalid={!!error}
            aria-describedby={describedBy}
            className="select-control"
            {...props}
          >
            {options
              ? options.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))
              : children}
          </select>
          <span className="select-arrow" aria-hidden="true">
            <ChevronDown size={16} />
          </span>
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

Select.displayName = 'Select'
