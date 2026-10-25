import React, { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import './AppShell.css'

export const AppShell: React.FC = () => {
  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem('fraudshield_sidebar_collapsed') === 'true'
    } catch {
      return false
    }
  })
  const [isMobileOpen, setIsMobileOpen] = useState(false)
  const location = useLocation()

  const handleToggleCollapse = () => {
    setIsCollapsed((prev) => {
      const next = !prev
      try {
        localStorage.setItem('fraudshield_sidebar_collapsed', String(next))
      } catch {
        // storage disabled
      }
      return next
    })
  }

  // Derive simple breadcrumbs from pathname
  const pathParts = location.pathname.split('/').filter(Boolean)
  const breadcrumbs = pathParts.map((part, idx) => {
    const href = '/' + pathParts.slice(0, idx + 1).join('/')
    const label =
      part.charAt(0).toUpperCase() + part.slice(1).replace(/-/g, ' ')
    return { label, href }
  })

  return (
    <div className="app-shell-root">
      <Sidebar
        isCollapsed={isCollapsed}
        onToggleCollapse={handleToggleCollapse}
        isMobileOpen={isMobileOpen}
        onCloseMobile={() => setIsMobileOpen(false)}
      />

      <div className="app-main-viewport">
        <Topbar
          onOpenMobileSidebar={() => setIsMobileOpen(true)}
          breadcrumbs={breadcrumbs}
        />

        <main id="main-content" className="app-content-area" tabIndex={-1}>
          <div className="app-content-container">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
