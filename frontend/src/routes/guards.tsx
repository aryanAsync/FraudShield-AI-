import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import type { UserRole } from '../api/types'
import { AccessRestricted } from '../components/feedback/AccessRestricted'
import { Skeleton } from '../components/ui/Skeleton'

export const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div style={{ padding: '32px', maxWidth: '1000px', margin: '40px auto' }}>
        <Skeleton height="32px" width="240px" />
        <div style={{ marginTop: '24px' }}>
          <Skeleton height="140px" borderRadius="8px" />
        </div>
        <div style={{ marginTop: '24px' }}>
          <Skeleton height="300px" borderRadius="8px" />
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    // Preserve intended destination path
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}

export const RoleRoute: React.FC<{
  roles: UserRole[]
  children: React.ReactNode
}> = ({ roles, children }) => {
  const { role, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div style={{ padding: '32px', maxWidth: '1000px', margin: '40px auto' }}>
        <Skeleton height="24px" width="200px" />
      </div>
    )
  }

  if (!role || !roles.includes(role)) {
    return <AccessRestricted requiredRole={roles.join(' or ')} />
  }

  return <>{children}</>
}
