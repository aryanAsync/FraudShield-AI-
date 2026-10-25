import React from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Plus, ExternalLink } from 'lucide-react'
import { transactionsApi } from '../../api'
import type { RiskLevel, TransactionSummaryResponse } from '../../api/types'
import { DataTable, type Column } from '../../components/data/DataTable'
import { Pagination } from '../../components/data/Pagination'
import { RiskBadge } from '../../components/risk/RiskBadge'
import { ProbabilityMeter } from '../../components/risk/ProbabilityMeter'
import { Button } from '../../components/ui/Button'
import { ErrorState } from '../../components/feedback/ErrorState'
import { formatAmount, formatTimestamp } from '../../lib/format'
import { useAuth } from '../../auth/AuthContext'
import './Transactions.css'

export const TransactionsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const { role } = useAuth()

  // Read URL query params
  const page = parseInt(searchParams.get('page') || '1', 10)
  const pageSize = parseInt(searchParams.get('page_size') || '20', 10)
  const riskLevel = searchParams.get('risk_level') || ''
  const predictedClass = searchParams.get('predicted_class')
  const sortBy = (searchParams.get('sort_by') || 'created_at') as
    | 'created_at'
    | 'amount'
    | 'transaction_time'
    | 'id'
  const sortOrder = (searchParams.get('sort_order') || 'desc') as 'asc' | 'desc'

  const queryParams = {
    page,
    page_size: pageSize,
    risk_level: riskLevel ? (riskLevel as RiskLevel) : undefined,
    predicted_class:
      predictedClass !== null && predictedClass !== ''
        ? parseInt(predictedClass, 10)
        : undefined,
    sort_by: sortBy,
    sort_order: sortOrder,
  }

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['transactions-list', queryParams],
    queryFn: () => transactionsApi.list(queryParams),
  })

  // URL state update helper
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

  const handleSort = (columnKey: string) => {
    const validSortFields = ['created_at', 'amount', 'transaction_time', 'id']
    if (!validSortFields.includes(columnKey)) return

    if (sortBy === columnKey) {
      updateParams({
        sort_order: sortOrder === 'asc' ? 'desc' : 'asc',
      })
    } else {
      updateParams({
        sort_by: columnKey,
        sort_order: 'desc',
        page: '1',
      })
    }
  }

  const columns: Column<TransactionSummaryResponse>[] = [
    {
      key: 'id',
      header: 'Txn ID',
      sortable: true,
      width: '100px',
      render: (row) => (
        <Link
          to={`/transactions/${row.id}`}
          className="mono txn-link"
          onClick={(e) => e.stopPropagation()}
        >
          #{row.id}
        </Link>
      ),
    },
    {
      key: 'created_at',
      header: 'Timestamp',
      sortable: true,
      render: (row) => {
        const { display } = formatTimestamp(row.created_at)
        return <span className="mono caption">{display}</span>
      },
    },
    {
      key: 'amount',
      header: 'Amount',
      sortable: true,
      align: 'right',
      render: (row) => (
        <span className="mono font-semibold tabular-nums">
          {formatAmount(row.amount)}
        </span>
      ),
    },
    {
      key: 'fraud_probability',
      header: 'Fraud Probability',
      render: (row) => {
        const pred = row.latest_prediction
        if (!pred) return <span className="caption">—</span>
        return (
          <ProbabilityMeter
            probability={pred.fraud_probability}
            threshold={pred.decision_threshold}
            size="sm"
          />
        )
      },
    },
    {
      key: 'risk_level',
      header: 'Risk Tier',
      render: (row) => {
        const pred = row.latest_prediction
        return <RiskBadge level={pred?.risk_level} size="sm" />
      },
    },
    {
      key: 'predicted_class',
      header: 'Model Decision',
      render: (row) => {
        const pred = row.latest_prediction
        if (!pred) return <span className="caption">—</span>
        return pred.predicted_class === 1 ? (
          <span className="predicted-fraud-tag">Flagged Risk</span>
        ) : (
          <span className="predicted-legit-tag">Legitimate</span>
        )
      },
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      width: '110px',
      render: (row) => (
        <div className="table-row-actions" onClick={(e) => e.stopPropagation()}>
          <Link
            to={`/transactions/${row.id}`}
            className="action-icon-link"
            title="Inspect transaction"
          >
            <ExternalLink size={15} />
          </Link>
        </div>
      ),
    },
  ]

  return (
    <div className="transactions-page">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Transaction Explorer</h1>
          <p className="caption">
            Browse stored financial transaction records, latest model risk evaluations, and PCA feature vectors.
          </p>
        </div>

        {(role === 'ANALYST' || role === 'ADMIN') && (
          <Link to="/score">
            <Button variant="primary" size="md" leftIcon={<Plus size={16} />}>
              Score New Transaction
            </Button>
          </Link>
        )}
      </div>

      {/* Filter Bar */}
      <div className="filter-bar panel">
        <div className="filter-group">
          <label htmlFor="filter-risk" className="caption font-semibold">
            Risk Tier:
          </label>
          <select
            id="filter-risk"
            className="filter-select"
            value={riskLevel}
            onChange={(e) => updateParams({ risk_level: e.target.value, page: '1' })}
          >
            <option value="">All Tiers</option>
            <option value="HIGH">HIGH Risk</option>
            <option value="MEDIUM">MEDIUM Risk</option>
            <option value="LOW">LOW Risk</option>
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="filter-class" className="caption font-semibold">
            Model Decision:
          </label>
          <select
            id="filter-class"
            className="filter-select"
            value={predictedClass ?? ''}
            onChange={(e) => updateParams({ predicted_class: e.target.value, page: '1' })}
          >
            <option value="">All Decisions</option>
            <option value="1">Flagged Fraud (Class 1)</option>
            <option value="0">Legitimate (Class 0)</option>
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="filter-sort" className="caption font-semibold">
            Sort:
          </label>
          <select
            id="filter-sort"
            className="filter-select"
            value={`${sortBy}-${sortOrder}`}
            onChange={(e) => {
              const [f, o] = e.target.value.split('-')
              updateParams({ sort_by: f, sort_order: o, page: '1' })
            }}
          >
            <option value="created_at-desc">Newest First</option>
            <option value="created_at-asc">Oldest First</option>
            <option value="amount-desc">Highest Amount</option>
            <option value="amount-asc">Lowest Amount</option>
          </select>
        </div>

        {(riskLevel || predictedClass !== null) && (
          <button
            type="button"
            className="clear-filters-btn caption"
            onClick={() => updateParams({ risk_level: null, predicted_class: null, page: '1' })}
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Error State */}
      {isError && (
        <ErrorState
          title="Failed to load transactions"
          error={error}
          onRetry={() => refetch()}
        />
      )}

      {/* Data Table */}
      {!isError && (
        <div className="table-wrapper-card">
          <DataTable<TransactionSummaryResponse>
            columns={columns}
            data={data?.items || []}
            isLoading={isLoading}
            sortBy={sortBy}
            sortOrder={sortOrder}
            onSort={handleSort}
            onRowClick={(row) => navigate(`/transactions/${row.id}`)}
            keyExtractor={(row) => row.id}
            emptyTitle="No transactions found"
            emptyMessage={
              riskLevel || predictedClass !== null
                ? 'No transactions match the selected risk filters.'
                : 'No transactions have been recorded in the database yet.'
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
