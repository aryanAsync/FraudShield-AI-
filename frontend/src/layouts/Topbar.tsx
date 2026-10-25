import React, { useEffect, useState } from 'react'
import { Menu, Activity, RefreshCw } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { healthApi } from '../api'
import './Topbar.css'

interface TopbarProps {
  onOpenMobileSidebar: () => void
  breadcrumbs?: { label: string; href?: string }[]
}

export const Topbar: React.FC<TopbarProps> = ({ onOpenMobileSidebar, breadcrumbs = [] }) => {
  const queryClient = useQueryClient()
  const [lastRefreshed, setLastRefreshed] = useState<string>('Just now')
  const [modelStatus, setModelStatus] = useState<'healthy' | 'unavailable' | 'checking'>('checking')
  const [isRefreshing, setIsRefreshing] = useState(false)

  const checkHealth = async () => {
    try {
      const res = await healthApi.check()
      if (res.model_loaded) {
        setModelStatus('healthy')
      } else {
        setModelStatus('unavailable')
      }
    } catch {
      setModelStatus('unavailable')
    }
  }

  useEffect(() => {
    void checkHealth()
    const interval = setInterval(() => {
      void checkHealth()
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleRefresh = async () => {
    setIsRefreshing(true)
    await queryClient.invalidateQueries()
    await checkHealth()
    const now = new Date()
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    setLastRefreshed(timeStr)
    setTimeout(() => {
      setIsRefreshing(false)
    }, 400)
  }

  return (
    <header className="app-topbar" aria-label="Page header">
      <div className="topbar-left">
        <button
          type="button"
          className="topbar-menu-btn"
          onClick={onOpenMobileSidebar}
          aria-label="Open navigation menu"
        >
          <Menu size={20} />
        </button>

        {breadcrumbs.length > 0 ? (
          <nav aria-label="Breadcrumb" className="topbar-breadcrumbs">
            <ol className="breadcrumb-list">
              {breadcrumbs.map((crumb, idx) => {
                const isLast = idx === breadcrumbs.length - 1
                return (
                  <li key={idx} className="breadcrumb-item">
                    {idx > 0 && <span className="breadcrumb-divider">/</span>}
                    {isLast || !crumb.href ? (
                      <span className="breadcrumb-current" aria-current={isLast ? 'page' : undefined}>
                        {crumb.label}
                      </span>
                    ) : (
                      <a href={crumb.href} className="breadcrumb-link">
                        {crumb.label}
                      </a>
                    )}
                  </li>
                )
              })}
            </ol>
          </nav>
        ) : (
          <div className="topbar-brand-context caption">Financial Risk Operations Console</div>
        )}
      </div>

      <div className="topbar-right">
        {/* Model Status Indicator */}
        <div
          className={`model-status-indicator status-${modelStatus}`}
          title={`Random Forest Model Status: ${modelStatus}`}
        >
          <Activity size={13} className="model-status-icon" />
          <span className="caption">
            {modelStatus === 'healthy'
              ? 'Model: Ready'
              : modelStatus === 'unavailable'
              ? 'Model: Offline'
              : 'Checking...'}
          </span>
        </div>

        {/* Freshness & Refresh */}
        <div className="data-freshness-block">
          <span className="freshness-text caption">Updated {lastRefreshed}</span>
          <button
            type="button"
            className="refresh-btn"
            onClick={handleRefresh}
            title="Refresh current page data"
            aria-label="Refresh data"
            disabled={isRefreshing}
          >
            <RefreshCw size={13} className={isRefreshing ? 'spin' : ''} />
          </button>
        </div>
      </div>
    </header>
  )
}
