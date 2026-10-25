import { describe, it, expect } from 'vitest'
import {
  getAvailableTransitions,
  ALLOWED_TRANSITIONS,
} from '../caseTransitions'

describe('Case State Machine Transitions', () => {
  it('correctly provides transitions for OPEN cases', () => {
    const transitions = getAvailableTransitions('OPEN')
    const targets = transitions.map((t) => t.to)
    expect(targets).toEqual(['IN_REVIEW', 'CLOSED'])
  })

  it('correctly provides transitions for IN_REVIEW cases', () => {
    const transitions = getAvailableTransitions('IN_REVIEW')
    const targets = transitions.map((t) => t.to)
    expect(targets).toEqual(['CONFIRMED_FRAUD', 'LEGITIMATE', 'OPEN'])
  })

  it('correctly provides transitions for CONFIRMED_FRAUD cases', () => {
    const transitions = getAvailableTransitions('CONFIRMED_FRAUD')
    const targets = transitions.map((t) => t.to)
    expect(targets).toEqual(['CLOSED'])
  })

  it('correctly provides transitions for LEGITIMATE cases', () => {
    const transitions = getAvailableTransitions('LEGITIMATE')
    const targets = transitions.map((t) => t.to)
    expect(targets).toEqual(['CLOSED'])
  })

  it('prohibits any transitions from terminal CLOSED status', () => {
    const transitions = getAvailableTransitions('CLOSED')
    expect(transitions).toHaveLength(0)
  })

  it('verifies terminal and determination flags in options', () => {
    const openTransitions = ALLOWED_TRANSITIONS.OPEN
    const closeOption = openTransitions.find((t) => t.to === 'CLOSED')
    expect(closeOption?.isTerminal).toBe(true)

    const inReviewTransitions = ALLOWED_TRANSITIONS.IN_REVIEW
    const fraudOption = inReviewTransitions.find((t) => t.to === 'CONFIRMED_FRAUD')
    expect(fraudOption?.isDetermination).toBe(true)
  })
})
