import React from 'react'
import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react'
import { Skeleton } from '../ui/Skeleton'
import { EmptyState } from '../feedback/EmptyState'
import './DataTable.css'

export interface Column<T> {
  key: string
  header: React.ReactNode
  render?: (row: T) => React.ReactNode
  sortable?: boolean
  align?: 'left' | 'center' | 'right'
  width?: string
  className?: string
}

export interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  isLoading?: boolean
  emptyMessage?: string
  emptyTitle?: string
  emptyAction?: React.ReactNode
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  onSort?: (columnKey: string) => void
  onRowClick?: (row: T) => void
  keyExtractor: (row: T) => string | number
  className?: string
}

export function DataTable<T>({
  columns,
  data,
  isLoading = false,
  emptyMessage = 'No records found matching your filters.',
  emptyTitle = 'No data available',
  emptyAction,
  sortBy,
  sortOrder,
  onSort,
  onRowClick,
  keyExtractor,
  className = '',
}: DataTableProps<T>): React.ReactElement {
  return (
    <div className={`table-container ${className}`}>
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col) => {
              const isSorted = sortBy === col.key
              return (
                <th
                  key={col.key}
                  scope="col"
                  style={{ width: col.width, textAlign: col.align || 'left' }}
                  className={`table-th ${col.sortable ? 'sortable' : ''} ${
                    col.align ? `align-${col.align}` : ''
                  }`}
                  aria-sort={isSorted ? (sortOrder === 'asc' ? 'ascending' : 'descending') : undefined}
                >
                  {col.sortable && onSort ? (
                    <button
                      type="button"
                      className="table-sort-btn"
                      onClick={() => onSort(col.key)}
                      aria-label={`Sort by ${col.key}`}
                    >
                      <span>{col.header}</span>
                      <span className="sort-icon" aria-hidden="true">
                        {isSorted ? (
                          sortOrder === 'asc' ? (
                            <ArrowUp size={13} />
                          ) : (
                            <ArrowDown size={13} />
                          )
                        ) : (
                          <ArrowUpDown size={13} className="sort-idle" />
                        )}
                      </span>
                    </button>
                  ) : (
                    <span>{col.header}</span>
                  )}
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          {isLoading && (
            <>
              {Array.from({ length: 6 }).map((_, rIdx) => (
                <tr key={`skeleton-${rIdx}`} className="table-row-skeleton">
                  {columns.map((col, cIdx) => (
                    <td key={`sk-cell-${cIdx}`} className="table-td">
                      <Skeleton height="16px" width={cIdx === 0 ? '70%' : '85%'} />
                    </td>
                  ))}
                </tr>
              ))}
            </>
          )}

          {!isLoading && data.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="table-empty-cell">
                <EmptyState
                  title={emptyTitle}
                  description={emptyMessage}
                  action={emptyAction}
                />
              </td>
            </tr>
          )}

          {!isLoading &&
            data.length > 0 &&
            data.map((row) => {
              const key = keyExtractor(row)
              return (
                <tr
                  key={key}
                  className={`table-row ${onRowClick ? 'clickable-row' : ''}`}
                  onClick={() => onRowClick?.(row)}
                  tabIndex={onRowClick ? 0 : undefined}
                  onKeyDown={(e) => {
                    if (onRowClick && (e.key === 'Enter' || e.key === ' ')) {
                      e.preventDefault()
                      onRowClick(row)
                    }
                  }}
                >
                  {columns.map((col) => {
                    const cellContent = col.render ? col.render(row) : (row as any)[col.key]
                    return (
                      <td
                        key={`${key}-${col.key}`}
                        style={{ textAlign: col.align || 'left' }}
                        className={`table-td ${col.align ? `align-${col.align}` : ''} ${
                          col.className || ''
                        }`}
                      >
                        {cellContent}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
        </tbody>
      </table>
    </div>
  )
}
