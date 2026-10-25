import React from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ExternalLink } from 'lucide-react'
import { casesApi } from '../../api'
import type { CaseResponse } from '../../api/types'
import { DataTable, type Column } from '../../components/data/DataTable'
import { Pagination } from '../../components/data/Pagination'
import { StatusBadge } from '../../components/risk/StatusBadge'
import { RiskBadge } from '../../components/risk/RiskBadge'
import { ErrorState } from '../../components/feedback/ErrorState'
import { formatAmount, formatTimestamp } from '../../lib/format'
import { useAuth } from '../../auth/AuthContext'
import './Investigations.css'

export const InvestigationsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const { user, role } = useAuth()

  const page = parseInt(searchParams.get('page') || '1', 10)
  const pageSize = parseInt(searchParams.get('page_size') || '20', 10)
  const statusFilter = searchParams.get('status') || ''
  const assignedUserId = searchParams.get('assigned_user_id')

  const queryParams = {
    page,
    page_size: pageSize,
    status: statusFilter || undefined,
    assigned_user_id: assignedUserId ? parseInt(assignedUserId, 10) : undefined,
  }

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['cases-list', queryParams],
    queryFn: () => casesApi.list(queryParams),
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

  const handlePageChange = (newPage: number) => {
    updateParams({ page: String(newPage) })
  }

  const isAnalyst = role === 'ANALYST'

  const columns: Column<CaseResponse>[] = [
    {
      key: 'id',
      header: 'Case ID',
      width: '100px',
      render: (row) => (
        <Link
          to={`/investigations/${row.id}`}
          className="mono case-link"
          onClick={(e) => e.stopPropagation()}
        >
          #{row.id}
        </Link>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      width: '140px',
      render: (row) => <StatusBadge status={row.status} size="sm" />,
    },
    {
      key: 'transaction_id',
      header: 'Linked Transaction',
      render: (row) => (
        <div className="linked-txn-cell">
          <Link
            to={`/transactions/${row.transaction_id}`}
            className="mono txn-link"
            onClick={(e) => e.stopPropagation()}
          >
            Txn #{row.transaction_id}
          </Link>
          {row.transaction && (
            <span className="caption mono tabular-nums">
              ({formatAmount(row.transaction.amount)})
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'risk_level',
      header: 'Model Risk',
      width: '120px',
      render: (row) => {
        const pred = row.latest_prediction
        return <RiskBadge level={pred?.risk_level} size="sm" />
      },
    },
    {
      key: 'assigned_to',
      header: 'Assignee',
      render: (row) => {
        if (!row.assigned_to) {
          return <span className="caption unassigned-label">Unassigned</span>
        }
        const isMe = user && row.assigned_user_id === user.id
        return (
          <span className={`caption ${isMe ? 'assigned-to-me' : ''}`}>
            {row.assigned_user?.name || row.assigned_to} {isMe && '(You)'}
          </span>
        )
      },
    },
    {
      key: 'created_at',
      header: 'Opened',
      render: (row) => {
        const { display } = formatTimestamp(row.created_at)
        return <span className="mono caption">{display}</span>
      },
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      width: '80px',
      render: (row) => (
        <div className="table-row-actions" onClick={(e) => e.stopPropagation()}>
          <Link
            to={`/investigations/${row.id}`}
            className="action-icon-link"
            title="Open investigation workspace"
          >
            <ExternalLink size={15} />
          </Link>
        </div>
      ),
    },
  ]

  return (
    <div className="investigations-page">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Fraud Investigation Queue</h1>
          <p className="caption">
            {isAnalyst
              ? 'Showing cases assigned to you and the unassigned triage queue.'
              : 'Enterprise triage queue for investigating flagged transactions, recording notes, and case adjudication.'}
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="filter-bar panel">
        <div className="filter-group">
          <label htmlFor="filter-case-status" className="caption font-semibold">
            Status:
          </label>
          <select
            id="filter-case-status"
            className="filter-select"
            value={statusFilter}
            onChange={(e) => updateParams({ status: e.target.value, page: '1' })}
          >
            <option value="">All Statuses</option>
            <option value="OPEN">OPEN</option>
            <option value="IN_REVIEW">IN_REVIEW</option>
            <option value="CONFIRMED_FRAUD">CONFIRMED_FRAUD</option>
            <option value="LEGITIMATE">LEGITIMATE</option>
            <option value="CLOSED">CLOSED</option>
          </select>
        </div>

        {user && (
          <div className="filter-group">
            <label htmlFor="filter-case-assignee" className="caption font-semibold">
              Assignment:
            </label>
            <select
              id="filter-case-assignee"
              className="filter-select"
              value={assignedUserId || ''}
              onChange={(e) => updateParams({ assigned_user_id: e.target.value, page: '1' })}
            >
              <option value="">All Assignees</option>
              <option value={String(user.id)}>Assigned to Me</option>
            </select>
          </div>
        )}

        {(statusFilter || assignedUserId) && (
          <button
            type="button"
            className="clear-filters-btn caption"
            onClick={() => updateParams({ status: null, assigned_user_id: null, page: '1' })}
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Error state */}
      {isError && (
        <ErrorState
          title="Failed to load investigation cases"
          error={error}
          onRetry={() => refetch()}
        />
      )}

      {/* Data Table */}
      {!isError && (
        <div className="table-wrapper-card">
          <DataTable<CaseResponse>
            columns={columns}
            data={data?.items || []}
            isLoading={isLoading}
            onRowClick={(row) => navigate(`/investigations/${row.id}`)}
            keyExtractor={(row) => row.id}
            emptyTitle="No investigation cases"
            emptyMessage={
              statusFilter || assignedUserId
                ? 'No investigation cases match the selected status or assignment filters.'
                : 'No cases have been opened in the investigation queue yet.'
            }
          />

          {data && (
            <Pagination
              page={page}
              pageSize={pageSize}
              total={data.total}
              totalPages={data.total_pages}
              onPageChange={handlePageChange}
              isLoading={isLoading}
            />
          )}
        </div>
      )}
    </div>
  )
}
