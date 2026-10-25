import type { CaseStatus } from '../api/types'

export interface StateTransitionOption {
  to: CaseStatus
  label: string
  description: string
  isTerminal?: boolean
  isDetermination?: boolean
  variant: 'primary' | 'secondary' | 'danger'
}

export const ALLOWED_TRANSITIONS: Record<CaseStatus, StateTransitionOption[]> = {
  OPEN: [
    {
      to: 'IN_REVIEW',
      label: 'Begin Review',
      description: 'Move case to active investigation review.',
      variant: 'primary',
    },
    {
      to: 'CLOSED',
      label: 'Close Case',
      description: 'Close without adjudication. This is irreversible.',
      isTerminal: true,
      variant: 'danger',
    },
  ],
  IN_REVIEW: [
    {
      to: 'CONFIRMED_FRAUD',
      label: 'Adjudicate as Confirmed Fraud',
      description: 'Record human determination of confirmed fraud.',
      isDetermination: true,
      variant: 'danger',
    },
    {
      to: 'LEGITIMATE',
      label: 'Adjudicate as Legitimate',
      description: 'Record human determination of legitimate transaction.',
      isDetermination: true,
      variant: 'secondary',
    },
    {
      to: 'OPEN',
      label: 'Return to Queue (Open)',
      description: 'Pause review and place case back in open triage.',
      variant: 'secondary',
    },
  ],
  CONFIRMED_FRAUD: [
    {
      to: 'CLOSED',
      label: 'Close Case',
      description: 'Finalize and archive this confirmed fraud case.',
      isTerminal: true,
      variant: 'primary',
    },
  ],
  LEGITIMATE: [
    {
      to: 'CLOSED',
      label: 'Close Case',
      description: 'Finalize and archive this resolved legitimate case.',
      isTerminal: true,
      variant: 'primary',
    },
  ],
  CLOSED: [],
}

export function getAvailableTransitions(currentStatus: CaseStatus): StateTransitionOption[] {
  return ALLOWED_TRANSITIONS[currentStatus] || []
}
