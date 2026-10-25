import React from 'react'
import { ShieldAlert } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '../ui/Button'
import { useAuth } from '../../auth/AuthContext'
import './Feedback.css'

interface AccessRestrictedProps {
  requiredRole?: string
  className?: string
}

export const AccessRestricted: React.FC<AccessRestrictedProps> = ({
  requiredRole,
  className = '',
}) => {
  const { user } = useAuth()

  return (
    <div className={`feedback-state access-restricted ${className}`} role="alert">
      <div className="feedback-icon restricted-icon" aria-hidden="true">
        <ShieldAlert size={36} />
      </div>
      <h2 className="feedback-title">Access Restricted</h2>
      <p className="feedback-desc caption">
        Your current role (<strong>{user?.role || 'Guest'}</strong>) does not have permission to access
        this resource.
        {requiredRole && ` This section requires ${requiredRole} privileges.`}
      </p>
      <div className="feedback-action">
        <Link to="/overview">
          <Button variant="primary" size="md">
            Return to Overview
          </Button>
        </Link>
      </div>
    </div>
  )
}
