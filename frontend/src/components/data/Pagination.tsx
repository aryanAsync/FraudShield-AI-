import React from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '../ui/Button'
import './Pagination.css'

interface PaginationProps {
  page: number
  pageSize: number
  total: number
  totalPages: number
  onPageChange: (newPage: number) => void
  isLoading?: boolean
}

export const Pagination: React.FC<PaginationProps> = ({
  page,
  pageSize,
  total,
  totalPages,
  onPageChange,
  isLoading = false,
}) => {
  if (total <= 0) return null

  const startIdx = (page - 1) * pageSize + 1
  const endIdx = Math.min(page * pageSize, total)

  return (
    <nav className="pagination-bar" aria-label="Pagination">
      <div className="pagination-info caption">
        Showing <span className="tabular-nums font-semibold">{startIdx}</span>–
        <span className="tabular-nums font-semibold">{endIdx}</span> of{' '}
        <span className="tabular-nums font-semibold">{total.toLocaleString()}</span> entries
      </div>

      <div className="pagination-controls">
        <Button
          variant="secondary"
          size="sm"
          disabled={page <= 1 || isLoading}
          onClick={() => onPageChange(page - 1)}
          aria-label="Previous page"
          leftIcon={<ChevronLeft size={16} />}
        >
          Previous
        </Button>

        <span className="pagination-page-indicator caption mono">
          Page {page} of {Math.max(totalPages, 1)}
        </span>

        <Button
          variant="secondary"
          size="sm"
          disabled={page >= totalPages || isLoading}
          onClick={() => onPageChange(page + 1)}
          aria-label="Next page"
          rightIcon={<ChevronRight size={16} />}
        >
          Next
        </Button>
      </div>
    </nav>
  )
}
