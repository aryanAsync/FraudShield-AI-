import React from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  LineChart,
  ListFilter,
  Calculator,
  ShieldAlert,
  FileText,
  Users,
  LogOut,
  Sun,
  Moon,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  Cpu,
} from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { useTheme } from '../design/theme'
import './Sidebar.css'

interface SidebarProps {
  isCollapsed: boolean
  onToggleCollapse: () => void
  isMobileOpen: boolean
  onCloseMobile: () => void
}

export const Sidebar: React.FC<SidebarProps> = ({
  isCollapsed,
  onToggleCollapse,
  isMobileOpen,
  onCloseMobile,
}) => {
  const { user, role, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()

  const isAdmin = role === 'ADMIN'
  const isAuditor = role === 'AUDITOR'
  const isAnalyst = role === 'ANALYST'

  return (
    <>
      {isMobileOpen && (
        <div className="sidebar-backdrop" onClick={onCloseMobile} aria-hidden="true" />
      )}

      <aside
        className={`app-sidebar ${isCollapsed ? 'collapsed' : ''} ${
          isMobileOpen ? 'mobile-open' : ''
        }`}
        aria-label="Main Navigation"
      >
        {/* Brand Header */}
        <div className="sidebar-header">
          <NavLink to="/overview" className="brand-link" onClick={onCloseMobile}>
            <div className="brand-logo-icon">
              <ShieldCheck size={20} className="brand-icon-svg" />
            </div>
            {!isCollapsed && (
              <div className="brand-text">
                <span className="brand-name-fraud">Fraud</span>
                <span className="brand-name-shield">Shield</span>
                <span className="brand-tag">AI</span>
              </div>
            )}
          </NavLink>

          <button
            type="button"
            className="sidebar-collapse-btn"
            onClick={onToggleCollapse}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>

        {/* Navigation Groups */}
        <nav className="sidebar-nav">
          {/* Group 1: Monitor */}
          <div className="nav-group">
            {!isCollapsed && <span className="nav-group-title">MONITOR</span>}
            <NavLink
              to="/overview"
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              onClick={onCloseMobile}
              title={isCollapsed ? 'Overview' : undefined}
            >
              <LayoutDashboard size={18} className="nav-icon" />
              {!isCollapsed && <span className="nav-label">Overview</span>}
            </NavLink>

            <NavLink
              to="/analytics"
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              onClick={onCloseMobile}
              title={isCollapsed ? 'Analytics' : undefined}
            >
              <LineChart size={18} className="nav-icon" />
              {!isCollapsed && <span className="nav-label">Analytics</span>}
            </NavLink>

            <NavLink
              to="/model-evaluation"
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              onClick={onCloseMobile}
              title={isCollapsed ? 'Model & Evaluation' : undefined}
            >
              <Cpu size={18} className="nav-icon" />
              {!isCollapsed && <span className="nav-label">Model &amp; Evaluation</span>}
            </NavLink>
          </div>

          {/* Group 2: Work */}
          <div className="nav-group">
            {!isCollapsed && <span className="nav-group-title">WORKFLOWS</span>}
            <NavLink
              to="/transactions"
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              onClick={onCloseMobile}
              title={isCollapsed ? 'Transactions' : undefined}
            >
              <ListFilter size={18} className="nav-icon" />
              {!isCollapsed && <span className="nav-label">Transactions</span>}
            </NavLink>

            {/* Score is permitted for Analyst and Admin */}
            {(isAnalyst || isAdmin) && (
              <NavLink
                to="/score"
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                onClick={onCloseMobile}
                title={isCollapsed ? 'Score Transaction' : undefined}
              >
                <Calculator size={18} className="nav-icon" />
                {!isCollapsed && <span className="nav-label">Score Input</span>}
              </NavLink>
            )}

            <NavLink
              to="/investigations"
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              onClick={onCloseMobile}
              title={isCollapsed ? 'Investigations' : undefined}
            >
              <ShieldAlert size={18} className="nav-icon" />
              {!isCollapsed && <span className="nav-label">Investigations</span>}
            </NavLink>
          </div>

          {/* Group 3: Governance */}
          {(isAdmin || isAuditor) && (
            <div className="nav-group">
              {!isCollapsed && <span className="nav-group-title">GOVERNANCE</span>}
              <NavLink
                to="/audit-logs"
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                onClick={onCloseMobile}
                title={isCollapsed ? 'Audit Logs' : undefined}
              >
                <FileText size={18} className="nav-icon" />
                {!isCollapsed && <span className="nav-label">Audit Logs</span>}
              </NavLink>

              {isAdmin && (
                <NavLink
                  to="/admin/users"
                  className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                  onClick={onCloseMobile}
                  title={isCollapsed ? 'User Management' : undefined}
                >
                  <Users size={18} className="nav-icon" />
                  {!isCollapsed && <span className="nav-label">Users & Access</span>}
                </NavLink>
              )}
            </div>
          )}
        </nav>

        {/* User Account / Footer */}
        <div className="sidebar-footer">
          <div className="user-profile-block">
            <div className="user-avatar" title={user?.email || 'User'}>
              {(user?.name || user?.email || 'U').charAt(0).toUpperCase()}
            </div>
            {!isCollapsed && (
              <div className="user-details">
                <span className="user-name">{user?.name || 'Analyst'}</span>
                <span className="user-role-badge">{role || 'ANALYST'}</span>
              </div>
            )}
          </div>

          <div className="footer-actions">
            <button
              type="button"
              className="footer-btn"
              onClick={toggleTheme}
              title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
              aria-label="Toggle visual theme"
            >
              {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            </button>

            <button
              type="button"
              className="footer-btn logout-btn"
              onClick={logout}
              title="Sign Out"
              aria-label="Sign out"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>
    </>
  )
}
