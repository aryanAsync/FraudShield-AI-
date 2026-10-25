import React, { useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import './Dialog.css'

export interface DialogProps {
  isOpen: boolean
  onClose: () => void
  title: string
  description?: string
  children: React.ReactNode
  maxWidth?: string
  role?: 'dialog' | 'alertdialog'
}

export const Dialog: React.FC<DialogProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  maxWidth = '520px',
  role = 'dialog',
}) => {
  const dialogRef = useRef<HTMLDivElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (isOpen) {
      previousFocusRef.current = document.activeElement as HTMLElement
      // Focus dialog on open
      setTimeout(() => {
        dialogRef.current?.focus()
      }, 50)

      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
          onClose()
        }
      }

      document.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'

      return () => {
        document.removeEventListener('keydown', handleKeyDown)
        document.body.style.overflow = ''
        previousFocusRef.current?.focus()
      }
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="dialog-backdrop" onClick={onClose} aria-hidden="true">
      <div
        ref={dialogRef}
        role={role}
        aria-modal="true"
        aria-labelledby="dialog-title"
        aria-describedby={description ? 'dialog-desc' : undefined}
        tabIndex={-1}
        className="dialog-panel"
        style={{ maxWidth }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="dialog-header">
          <div className="dialog-title-group">
            <h3 id="dialog-title" className="dialog-title">
              {title}
            </h3>
            {description && (
              <p id="dialog-desc" className="dialog-description caption">
                {description}
              </p>
            )}
          </div>
          <button
            type="button"
            className="dialog-close-btn"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <X size={16} />
          </button>
        </div>

        <div className="dialog-body">{children}</div>
      </div>
    </div>
  )
}
