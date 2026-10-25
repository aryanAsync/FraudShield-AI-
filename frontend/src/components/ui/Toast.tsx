import React, { createContext, useContext, useState, useCallback } from 'react'
import { AlertCircle, CheckCircle2, Info, X, AlertTriangle } from 'lucide-react'
import './Toast.css'

export type ToastType = 'success' | 'danger' | 'info' | 'warning'

export interface ToastItem {
  id: string
  title?: string
  message: string
  type: ToastType
  duration?: number
}

interface ToastContextType {
  toast: (item: Omit<ToastItem, 'id'>) => void
  success: (message: string, title?: string) => void
  error: (message: string, title?: string) => void
  info: (message: string, title?: string) => void
  warning: (message: string, title?: string) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const toast = useCallback(
    ({ duration = 4000, ...rest }: Omit<ToastItem, 'id'>) => {
      const id = Math.random().toString(36).substring(2, 9)
      const newToast: ToastItem = { id, duration, ...rest }
      setToasts((prev) => [...prev, newToast])

      if (duration > 0) {
        setTimeout(() => {
          removeToast(id)
        }, duration)
      }
    },
    [removeToast]
  )

  const success = useCallback(
    (message: string, title?: string) => {
      toast({ message, title, type: 'success' })
    },
    [toast]
  )

  const error = useCallback(
    (message: string, title?: string) => {
      // Errors stay longer for readability
      toast({ message, title, type: 'danger', duration: 7000 })
    },
    [toast]
  )

  const info = useCallback(
    (message: string, title?: string) => {
      toast({ message, title, type: 'info' })
    },
    [toast]
  )

  const warning = useCallback(
    (message: string, title?: string) => {
      toast({ message, title, type: 'warning' })
    },
    [toast]
  )

  return (
    <ToastContext.Provider value={{ toast, success, error, info, warning }}>
      {children}
      <aside className="toast-viewport" aria-label="Notifications" aria-live="polite">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`toast-item toast-${t.type}`}
            role={t.type === 'danger' ? 'alert' : 'status'}
          >
            <div className="toast-icon">
              {t.type === 'success' && <CheckCircle2 size={18} />}
              {t.type === 'danger' && <AlertCircle size={18} />}
              {t.type === 'warning' && <AlertTriangle size={18} />}
              {t.type === 'info' && <Info size={18} />}
            </div>
            <div className="toast-content">
              {t.title && <div className="toast-title">{t.title}</div>}
              <div className="toast-message">{t.message}</div>
            </div>
            <button
              type="button"
              className="toast-close"
              onClick={() => removeToast(t.id)}
              aria-label="Dismiss notification"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </aside>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextType {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}
