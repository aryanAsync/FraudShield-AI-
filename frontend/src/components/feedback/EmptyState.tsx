import React from 'react'
import { FolderOpen } from 'lucide-react'
import './Feedback.css'

interface EmptyStateProps {
  icon?: React.ReactNode
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className = '',
}) => {
  return (
    <div className={`feedback-state empty-state ${className}`} role="status">
      <div className="feedback-icon" aria-hidden="true">
        {icon || <FolderOpen size={32} />}
      </div>
      <h3 className="feedback-title">{title}</h3>
      {description && <p className="feedback-desc caption">{description}</p>}
      {action && <div className="feedback-action">{action}</div>}
    </div>
  )
}
