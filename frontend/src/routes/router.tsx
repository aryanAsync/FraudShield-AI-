import React from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppShell } from '../layouts/AppShell'
import { ProtectedRoute, RoleRoute } from './guards'

// Pages
import { LoginPage } from '../features/auth/LoginPage'
import { OverviewPage } from '../features/overview/OverviewPage'
import { AnalyticsPage } from '../features/analytics/AnalyticsPage'
import { TransactionsPage } from '../features/transactions/TransactionsPage'
import { TransactionDetailPage } from '../features/transactions/TransactionDetailPage'
import { ScorePage } from '../features/transactions/ScorePage'
import { InvestigationsPage } from '../features/investigations/InvestigationsPage'
import { CaseDetailPage } from '../features/investigations/CaseDetailPage'
import { AuditLogsPage } from '../features/audit/AuditLogsPage'
import { UsersPage } from '../features/users/UsersPage'
import { ModelEvaluationPage } from '../features/models/ModelEvaluationPage'
import { NotFoundPage } from '../components/feedback/NotFoundPage'

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppShell />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <Navigate to="/overview" replace />,
      },
      {
        path: 'overview',
        element: <OverviewPage />,
      },
      {
        path: 'analytics',
        element: <AnalyticsPage />,
      },
      {
        path: 'transactions',
        element: <TransactionsPage />,
      },
      {
        path: 'transactions/:id',
        element: <TransactionDetailPage />,
      },
      {
        path: 'score',
        element: (
          <RoleRoute roles={['ANALYST', 'ADMIN']}>
            <ScorePage />
          </RoleRoute>
        ),
      },
      {
        path: 'investigations',
        element: <InvestigationsPage />,
      },
      {
        path: 'investigations/:caseId',
        element: <CaseDetailPage />,
      },
      {
        path: 'model-evaluation',
        element: <ModelEvaluationPage />,
      },
      {
        path: 'audit-logs',
        element: (
          <RoleRoute roles={['ADMIN', 'AUDITOR']}>
            <AuditLogsPage />
          </RoleRoute>
        ),
      },
      {
        path: 'admin/users',
        element: (
          <RoleRoute roles={['ADMIN']}>
            <UsersPage />
          </RoleRoute>
        ),
      },
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
])
