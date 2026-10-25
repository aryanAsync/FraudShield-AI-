import React from 'react'
import './Skeleton.css'

interface SkeletonProps {
  width?: string | number
  height?: string | number
  borderRadius?: string
  className?: string
  count?: number
}

export const Skeleton: React.FC<SkeletonProps> = ({
  width = '100%',
  height = '20px',
  borderRadius = 'var(--radius-sm)',
  className = '',
  count = 1,
}) => {
  const elements = Array.from({ length: count }, (_, i) => (
    <div
      key={i}
      className={`skeleton-block ${className}`}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
        borderRadius,
      }}
      aria-hidden="true"
    />
  ))

  if (count === 1) return elements[0]

  return <div className="skeleton-group">{elements}</div>
}
