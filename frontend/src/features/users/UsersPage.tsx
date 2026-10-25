import React, { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  UserPlus,
  Edit2,
  CheckCircle2,
  XCircle,
} from 'lucide-react'
import { usersApi } from '../../api'
import type { UserResponse, UserRole } from '../../api/types'
import { DataTable, type Column } from '../../components/data/DataTable'
import { Pagination } from '../../components/data/Pagination'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Select } from '../../components/ui/Select'
import { Dialog } from '../../components/ui/Dialog'
import { ErrorState } from '../../components/feedback/ErrorState'
import { useToast } from '../../components/ui/Toast'
import { formatTimestamp } from '../../lib/format'
import './UsersPage.css'

export const UsersPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const toast = useToast()

  const page = parseInt(searchParams.get('page') || '1', 10)
  const pageSize = parseInt(searchParams.get('page_size') || '20', 10)
  const roleFilter = searchParams.get('role') as UserRole | null
  const activeFilterStr = searchParams.get('is_active')

  const queryParams = {
    page,
    page_size: pageSize,
    role: roleFilter || undefined,
    is_active: activeFilterStr !== null ? activeFilterStr === 'true' : undefined,
  }

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['users-list', queryParams],
    queryFn: () => usersApi.list(queryParams),
  })

  // Create Modal state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [createName, setCreateName] = useState('')
  const [createEmail, setCreateEmail] = useState('')
  const [createPassword, setCreatePassword] = useState('')
  const [createRole, setCreateRole] = useState<UserRole>('ANALYST')
  const [createError, setCreateError] = useState<string | null>(null)

  // Edit Modal state
  const [editingUser, setEditingUser] = useState<UserResponse | null>(null)
  const [editName, setEditName] = useState('')
  const [editRole, setEditRole] = useState<UserRole>('ANALYST')
  const [editIsActive, setEditIsActive] = useState<boolean>(true)
  const [editPassword, setEditPassword] = useState('')
  const [editError, setEditError] = useState<string | null>(null)

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

  // Create User Mutation
  const createUserMutation = useMutation({
    mutationFn: (payload: { name: string; email: string; password: string; role: UserRole }) =>
      usersApi.create(payload),
    onSuccess: (newUser) => {
      toast.success(`User ${newUser.name} created successfully.`)
      setIsCreateModalOpen(false)
      setCreateName('')
      setCreateEmail('')
      setCreatePassword('')
      setCreateRole('ANALYST')
      setCreateError(null)
      queryClient.invalidateQueries({ queryKey: ['users-list'] })
    },
    onError: (err: any) => {
      setCreateError(err?.message || 'Failed to create user account.')
    },
  })

  // Edit User Mutation
  const updateUserMutation = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: number
      payload: { name?: string; role?: UserRole; is_active?: boolean; password?: string }
    }) => usersApi.update(id, payload),
    onSuccess: (updated) => {
      toast.success(`User ${updated.name} updated successfully.`)
      setEditingUser(null)
      setEditError(null)
      queryClient.invalidateQueries({ queryKey: ['users-list'] })
    },
    onError: (err: any) => {
      setEditError(err?.message || 'Failed to update user account.')
    },
  })

  const openEditModal = (u: UserResponse) => {
    setEditingUser(u)
    setEditName(u.name)
    setEditRole(u.role)
    setEditIsActive(u.is_active)
    setEditPassword('')
    setEditError(null)
  }

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setCreateError(null)
    if (!createName.trim()) {
      setCreateError('Name is required.')
      return
    }
    if (!createEmail.trim()) {
      setCreateError('Email is required.')
      return
    }
    if (createPassword.length < 8) {
      setCreateError('Password must be at least 8 characters long.')
      return
    }

    createUserMutation.mutate({
      name: createName.trim(),
      email: createEmail.trim().toLowerCase(),
      password: createPassword,
      role: createRole,
    })
  }

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingUser) return
    setEditError(null)

    const payload: { name?: string; role?: UserRole; is_active?: boolean; password?: string } = {}
    if (editName.trim() !== editingUser.name) payload.name = editName.trim()
    if (editRole !== editingUser.role) payload.role = editRole
    if (editIsActive !== editingUser.is_active) payload.is_active = editIsActive
    if (editPassword.trim()) {
      if (editPassword.length < 8) {
        setEditError('New password must be at least 8 characters.')
        return
      }
      payload.password = editPassword
    }

    updateUserMutation.mutate({ id: editingUser.id, payload })
  }

  const columns: Column<UserResponse>[] = [
    {
      key: 'name',
      header: 'Name',
      render: (row) => (
        <div className="user-name-cell">
          <span className="font-semibold">{row.name}</span>
          <span className="caption mono">{row.email}</span>
        </div>
      ),
    },
    {
      key: 'role',
      header: 'Role',
      width: '120px',
      render: (row) => (
        <span className={`role-pill role-${row.role.toLowerCase()}`}>
          {row.role}
        </span>
      ),
    },
    {
      key: 'is_active',
      header: 'Status',
      width: '120px',
      render: (row) => (
        <span className={`status-pill ${row.is_active ? 'active' : 'inactive'}`}>
          {row.is_active ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
          <span>{row.is_active ? 'Active' : 'Deactivated'}</span>
        </span>
      ),
    },
    {
      key: 'last_login_at',
      header: 'Last Login',
      render: (row) => {
        if (!row.last_login_at) return <span className="caption">—</span>
        return <span className="mono caption">{formatTimestamp(row.last_login_at).display}</span>
      },
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      width: '90px',
      render: (row) => (
        <Button
          variant="secondary"
          size="sm"
          onClick={() => openEditModal(row)}
          leftIcon={<Edit2 size={13} />}
        >
          Edit
        </Button>
      ),
    },
  ]

  return (
    <div className="users-page">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">User & Access Management</h1>
          <p className="caption">
            Manage enterprise analyst, auditor, and administrator accounts and enforce role-based access permissions.
          </p>
        </div>

        <Button
          variant="primary"
          size="md"
          onClick={() => setIsCreateModalOpen(true)}
          leftIcon={<UserPlus size={16} />}
        >
          Create New User
        </Button>
      </div>

      {/* Filter Bar */}
      <div className="filter-bar panel">
        <div className="filter-group">
          <label htmlFor="filter-user-role" className="caption font-semibold">
            Role:
          </label>
          <select
            id="filter-user-role"
            className="filter-select"
            value={roleFilter || ''}
            onChange={(e) => updateParams({ role: e.target.value || null, page: '1' })}
          >
            <option value="">All Roles</option>
            <option value="ANALYST">Analyst</option>
            <option value="AUDITOR">Auditor</option>
            <option value="ADMIN">Administrator</option>
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="filter-user-status" className="caption font-semibold">
            Account Status:
          </label>
          <select
            id="filter-user-status"
            className="filter-select"
            value={activeFilterStr ?? ''}
            onChange={(e) => updateParams({ is_active: e.target.value || null, page: '1' })}
          >
            <option value="">All Accounts</option>
            <option value="true">Active Only</option>
            <option value="false">Deactivated Only</option>
          </select>
        </div>

        {(roleFilter || activeFilterStr !== null) && (
          <button
            type="button"
            className="clear-filters-btn caption"
            onClick={() => updateParams({ role: null, is_active: null, page: '1' })}
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Error State */}
      {isError && (
        <ErrorState
          title="Failed to load user accounts"
          error={error}
          onRetry={() => refetch()}
        />
      )}

      {/* Users Table */}
      {!isError && (
        <div className="table-wrapper-card">
          <DataTable<UserResponse>
            columns={columns}
            data={data?.items || []}
            isLoading={isLoading}
            keyExtractor={(row) => row.id}
            emptyTitle="No users found"
            emptyMessage={
              roleFilter || activeFilterStr !== null
                ? 'No user accounts match the selected filters.'
                : 'No users registered yet.'
            }
          />

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

      {/* Create User Dialog */}
      <Dialog
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create New User Account"
        description="Register a new analyst, auditor, or administrator with secure modern password hashing."
      >
        <form onSubmit={handleCreateSubmit} className="user-dialog-form">
          {createError && <p className="input-message input-error">{createError}</p>}

          <Input
            id="create-name"
            label="Full Display Name"
            placeholder="Jane Analyst"
            value={createName}
            onChange={(e) => setCreateName(e.target.value)}
            required
          />

          <Input
            id="create-email"
            label="Work Email Address"
            type="email"
            placeholder="jane@fraudshield.ai"
            value={createEmail}
            onChange={(e) => setCreateEmail(e.target.value)}
            required
          />

          <Input
            id="create-password"
            label="Initial Account Password"
            type="password"
            placeholder="Minimum 8 characters"
            value={createPassword}
            onChange={(e) => setCreatePassword(e.target.value)}
            helperText="Minimum 8 characters. Hashed via bcrypt on the backend."
            required
          />

          <Select
            id="create-role"
            label="System RBAC Role"
            value={createRole}
            onChange={(e) => setCreateRole(e.target.value as UserRole)}
            options={[
              { value: 'ANALYST', label: 'ANALYST — Triage, score, investigate cases, add notes' },
              { value: 'AUDITOR', label: 'AUDITOR — Read-only compliance & audit log inspection' },
              { value: 'ADMIN', label: 'ADMIN — Full system governance and user administration' },
            ]}
          />

          <div className="dialog-footer" style={{ margin: '16px -20px -20px -20px' }}>
            <Button
              variant="secondary"
              size="md"
              onClick={() => setIsCreateModalOpen(false)}
              disabled={createUserMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={createUserMutation.isPending}
            >
              Create Account
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Edit User Dialog */}
      <Dialog
        isOpen={!!editingUser}
        onClose={() => setEditingUser(null)}
        title={`Edit User: ${editingUser?.name}`}
        description="Update user name, system role, account status, or perform a password reset."
      >
        <form onSubmit={handleEditSubmit} className="user-dialog-form">
          {editError && <p className="input-message input-error">{editError}</p>}

          <Input
            id="edit-name"
            label="Full Display Name"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            required
          />

          <div className="input-field-group">
            <span className="input-label">Email Address</span>
            <span className="mono caption">{editingUser?.email} (immutable)</span>
          </div>

          <Select
            id="edit-role"
            label="System Role"
            value={editRole}
            onChange={(e) => setEditRole(e.target.value as UserRole)}
            options={[
              { value: 'ANALYST', label: 'ANALYST' },
              { value: 'AUDITOR', label: 'AUDITOR' },
              { value: 'ADMIN', label: 'ADMIN' },
            ]}
          />

          <div className="checkbox-field">
            <label className="checkbox-label caption font-semibold">
              <input
                type="checkbox"
                checked={editIsActive}
                onChange={(e) => setEditIsActive(e.target.checked)}
              />
              <span>Account is Active</span>
            </label>
            <p className="caption" style={{ color: 'var(--text-tertiary)', marginTop: '2px' }}>
              Deactivating revokes login access and denies ongoing sessions.
            </p>
          </div>

          <Input
            id="edit-password"
            label="Reset Password (Leave blank to keep current)"
            type="password"
            placeholder="New password (optional)"
            value={editPassword}
            onChange={(e) => setEditPassword(e.target.value)}
            helperText="Leave empty if password should remain unchanged."
          />

          <div className="dialog-footer" style={{ margin: '16px -20px -20px -20px' }}>
            <Button
              variant="secondary"
              size="md"
              onClick={() => setEditingUser(null)}
              disabled={updateUserMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={updateUserMutation.isPending}
            >
              Save Changes
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  )
}
