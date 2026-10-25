import { describe, it, expect } from 'vitest'
import { ApiClientError } from '../client'

describe('ApiClientError', () => {
  it('constructs with status and getters', () => {
    const err = new ApiClientError('Invalid credentials', 401, null, { detail: 'Invalid credentials' })
    expect(err.message).toBe('Invalid credentials')
    expect(err.status).toBe(401)
    expect(err.isUnauthorized).toBe(true)
    expect(err.isForbidden).toBe(false)
  })

  it('handles array details from FastAPI 422 validation errors', () => {
    const validationErrors = [
      { loc: ['body', 'email'], msg: 'field required', type: 'value_error.missing' },
      { loc: ['body', 'password'], msg: 'field required', type: 'value_error.missing' },
    ]
    const err = new ApiClientError(
      'Validation failed',
      422,
      validationErrors,
      { detail: validationErrors }
    )
    expect(err.status).toBe(422)
    expect(Array.isArray(err.details)).toBe(true)
    expect(err.details?.length).toBe(2)
  })
})
