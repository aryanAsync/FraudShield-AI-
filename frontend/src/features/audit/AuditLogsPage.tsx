import React, { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Lock,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'
import { auditApi } from '../../api'
import { Pagination } from '../../components/data/Pagination'
import { Skeleton } from '../../components/ui/Skeleton'
import { ErrorState } from '../../components/feedback/ErrorState'
import { EmptyState } from '../../components/feedback/EmptyState'
import { formatTimestamp } from '../../lib/format'
import './AuditLogsPage.css'

export const AuditLogsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams()

  const page = parseInt(searchParams.get('page') || '1', 10)
  const pageSize = parseInt(searchParams.get('page_size') || '20', 10)
  const actionFilter = searchParams.get('action') || ''
  const entityTypeFilter = searchParams.get('entity_type') || ''
  const actorIdFilter = searchParams.get('actor_id') || ''

  const [expandedLogIds, setExpandedLogIds] = useState<Set<number>>(new Set())

  const toggleExpand = (id: number) => {
    setExpandedLogIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const queryParams = {
    page,
    page_size: pageSize,
    action: actionFilter || undefined,
    entity_type: entityTypeFilter || undefined,
    actor_id: actorIdFilter || undefined,
  }

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['audit-logs-list', queryParams],
    queryFn: () => auditApi.list(queryParams),
  })

  const updateParams = (newParams: Record<string, string | null>) => {
    const updated = new URLSearchParams(searchParams)
    for (const [key, val] of Object.entries(newParams)) {
      if (val === null || val === '') {
        updated.delete(key)
      } else {
        updated.set(key, val)
      }
    }
    setSearchParams(updated)
  }

  return (
    <div className="audit-logs-page">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Compliance Audit Trail</h1>
          <p className="caption">
            Immutable, append-only security ledger recording all user authentications, risk scoring,
            case adjudications, and access mutations.
          </p>
        </div>

        <div className="audit-immutable-indicator caption">
          <Lock size={13} />
          <span>Server-Enforced Immutable Ledger</span>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="filter-bar panel">
        <div className="filter-group">
          <label htmlFor="filter-action" className="caption font-semibold">
            Action:
          </label>
          <select
            id="filter-action"
            className="filter-select"
            value={actionFilter}
            onChange={(e) => updateParams({ action: e.target.value, page: '1' })}
          >
            <option value="">All Actions</option>
            <option value="LOGIN_SUCCESS">LOGIN_SUCCESS</option>
            <option value="LOGIN_FAILED">LOGIN_FAILED</option>
            <option value="CASE_CREATED">CASE_CREATED</option>
            <option value="CASE_STATUS_CHANGED">CASE_STATUS_CHANGED</option>
            <option value="CASE_ASSIGNED">CASE_ASSIGNED</option>
            <option value="CASE_NOTE_ADDED">CASE_NOTE_ADDED</option>
            <option value="USER_CREATED">USER_CREATED</option>
            <option value="USER_UPDATED">USER_UPDATED</option>
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="filter-entity-type" className="caption font-semibold">
            Entity Type:
          </label>
          <select
            id="filter-entity-type"
            className="filter-select"
            value={entityTypeFilter}
            onChange={(e) => updateParams({ entity_type: e.target.value, page: '1' })}
          >
            <option value="">All Entities</option>
            <option value="investigation_case">Investigation Case</option>
            <option value="user">User Account</option>
            <option value="transaction">Transaction</option>
          </select>
        </div>

        {(actionFilter || entityTypeFilter || actorIdFilter) && (
          <button
            type="button"
            className="clear-filters-btn caption"
            onClick={() =>
              updateParams({ action: null, entity_type: null, actor_id: null, page: '1' })
            }
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Error state */}
      {isError && (
        <ErrorState
          title="Failed to load audit logs"
          error={error}
          onRetry={() => refetch()}
        />
      )}

      {/* Audit Log Table */}
      {!isError && (
        <div className="table-wrapper-card panel">
          <div className="table-container" style={{ border: 'none' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: '40px' }}></th>
                  <th style={{ width: '100px' }}>Event ID</th>
                  <th>Timestamp</th>
                  <th>Action</th>
                  <th>Actor ID</th>
                  <th>Target Entity</th>
                  <th>Target ID</th>
                </tr>
              </thead>
              <tbody>
                {isLoading && (
                  <>
                    {Array.from({ length: 6 }).map((_, rIdx) => (
                      <tr key={`sk-row-${rIdx}`} className="table-row-skeleton">
                        <td colSpan={7} style={{ padding: '12px' }}>
                          <Skeleton height="18px" />
                        </td>
                      </tr>
                    ))}
                  </>
                )}

                {!isLoading && (!data?.items || data.items.length === 0) && (
                  <tr>
                    <td colSpan={7} className="table-empty-cell">
                      <EmptyState
                        title="No audit events found"
                        description={
                          actionFilter || entityTypeFilter
                            ? 'No audit events match the selected filters.'
                            : 'No security audit events have been logged yet.'
                        }
                      />
                    </td>
                  </tr>
                )}

                {!isLoading &&
                  data?.items.map((log) => {
                    const isExpanded = expandedLogIds.has(log.id)
                    const hasDetails = log.details && Object.keys(log.details).length > 0

                    return (
                      <React.Fragment key={log.id}>
                        <tr
                          className={`table-row ${hasDetails ? 'clickable-row' : ''}`}
                          onClick={() => hasDetails && toggleExpand(log.id)}
                        >
                          <td style={{ textAlign: 'center' }}>
                            {hasDetails && (
                              <button
                                type="button"
                                className="expand-chevron-btn"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  toggleExpand(log.id)
                                }}
                                aria-label={isExpanded ? 'Collapse event details' : 'Expand event details'}
                              >
                                {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                              </button>
                            )}
                          </td>
                          <td className="mono caption">#{log.id}</td>
                          <td className="mono caption">{formatTimestamp(log.created_at).display}</td>
                          <td>
                            <span className="action-pill mono font-semibold">{log.action}</span>
                          </td>
                          <td className="mono caption">{log.actor_id || 'System / Unauth'}</td>
                          <td className="caption font-semibold">{log.entity_type}</td>
                          <td className="mono caption">#{log.entity_id}</td>
                        </tr>

                        {/* Expandable JSON details row */}
                        {isExpanded && hasDetails && (
                          <tr className="audit-details-row">
                            <td colSpan={7}>
                              <div className="audit-json-box panel-subtle">
                                <span className="caption font-semibold">Structured Event Metadata:</span>
                                <pre className="mono">{JSON.stringify(log.details, null, 2)}</pre>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    )
                  })}
              </tbody>
            </table>
          </div>

          {data && (
            <Pagination
              page={page}
              pageSize={pageSize}
              total={data.total}
              totalPages={data.total_pages}
              onPageChange={(p) => updateParams({ page: String(p) })}
              isLoading={isLoading}
            />
          )}
        </div>
      )}
    </div>
  )
}
