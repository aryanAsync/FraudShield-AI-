import React, { forwardRef } from 'react'
import { Loader2 } from 'lucide-react'
import './Button.css'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'tertiary' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = 'secondary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      disabled,
      className = '',
      type = 'button',
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || isLoading

    return (
      <button
        ref={ref}
        type={type}
        disabled={isDisabled}
        aria-busy={isLoading}
        aria-disabled={isDisabled}
        className={`btn btn-${variant} btn-${size} ${isLoading ? 'btn-loading' : ''} ${className}`}
        {...props}
      >
        {isLoading && <Loader2 className="btn-spinner" size={size === 'sm' ? 14 : 16} />}
        {!isLoading && leftIcon && <span className="btn-icon-left">{leftIcon}</span>}
        <span className="btn-label">{children}</span>
        {!isLoading && rightIcon && <span className="btn-icon-right">{rightIcon}</span>}
      </button>
    )
  }
)

Button.displayName = 'Button'
