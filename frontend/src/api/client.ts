import type { ApiErrorPayload, ApiValidationErrorDetail } from './types'

export class ApiClientError extends Error {
  public status: number
  public details: ApiValidationErrorDetail[] | null
  public rawPayload: ApiErrorPayload | null

  constructor(
    message: string,
    status: number,
    details: ApiValidationErrorDetail[] | null = null,
    rawPayload: ApiErrorPayload | null = null
  ) {
    super(message)
    this.name = 'ApiClientError'
    this.status = status
    this.details = details
    this.rawPayload = rawPayload
  }

  get isUnauthorized(): boolean {
    return this.status === 401
  }

  get isForbidden(): boolean {
    return this.status === 403
  }

  get isNotFound(): boolean {
    return this.status === 404
  }

  get isConflict(): boolean {
    return this.status === 409
  }

  get isValidationError(): boolean {
    return this.status === 422
  }
}

// Token storage key
const TOKEN_KEY = 'fraudshield_token'

// In-memory token holder
let inMemoryToken: string | null = null

// Restore from sessionStorage on initialize if present
try {
  const stored = sessionStorage.getItem(TOKEN_KEY)
  if (stored) {
    inMemoryToken = stored
  }
} catch {
  // Storage might be restricted
}

export function setAuthToken(token: string | null): void {
  inMemoryToken = token
  try {
    if (token) {
      sessionStorage.setItem(TOKEN_KEY, token)
    } else {
      sessionStorage.removeItem(TOKEN_KEY)
    }
  } catch {
    // Storage restricted
  }
}

export function getAuthToken(): string | null {
  return inMemoryToken
}

// Event listener for global 401 unauthorized handling
type UnauthorizedListener = () => void
const unauthorizedListeners: Set<UnauthorizedListener> = new Set()

export function onUnauthorized(listener: UnauthorizedListener): () => void {
  unauthorizedListeners.add(listener)
  return () => {
    unauthorizedListeners.delete(listener)
  }
}

function notifyUnauthorized(): void {
  for (const listener of unauthorizedListeners) {
    try {
      listener()
    } catch (e) {
      console.error('Error in unauthorized listener', e)
    }
  }
}

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '')

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | null | undefined>
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { params, headers, ...restOptions } = options

  let url = `${BASE_URL}${endpoint}`
  if (params) {
    const searchParams = new URLSearchParams()
    for (const [key, value] of Object.entries(params)) {
      if (value !== null && value !== undefined && value !== '') {
        searchParams.append(key, String(value))
      }
    }
    const queryString = searchParams.toString()
    if (queryString) {
      url += (url.includes('?') ? '&' : '?') + queryString
    }
  }

  const reqHeaders: Record<string, string> = {
    Accept: 'application/json',
    ...(headers as Record<string, string>),
  }

  if (inMemoryToken) {
    reqHeaders['Authorization'] = `Bearer ${inMemoryToken}`
  }

  if (restOptions.body && typeof restOptions.body === 'string' && !reqHeaders['Content-Type']) {
    reqHeaders['Content-Type'] = 'application/json'
  }

  let response: Response
  try {
    response = await fetch(url, {
      ...restOptions,
      headers: reqHeaders,
    })
  } catch {
    throw new ApiClientError(
      'Unable to connect to FraudShield AI service. Please verify your network connection and server status.',
      0,
      null,
      null
    )
  }

  if (response.status === 401) {
    notifyUnauthorized()
  }

  if (!response.ok) {
    let payload: ApiErrorPayload | null = null
    let message = `Request failed with HTTP status ${response.status}`
    let details: ApiValidationErrorDetail[] | null = null

    try {
      payload = await response.json()
      if (payload) {
        if (typeof payload.detail === 'string') {
          message = payload.detail
        } else if (Array.isArray(payload.detail)) {
          details = payload.detail
          message = details.map((d) => d.msg).join('; ') || 'Validation error'
        } else if (payload.message) {
          message = payload.message
        } else if (Array.isArray(payload.details)) {
          details = payload.details
          message = details.map((d) => d.msg).join('; ') || 'Validation error'
        }
      }
    } catch {
      // Non-JSON error payload
    }

    throw new ApiClientError(message, response.status, details, payload)
  }

  if (response.status === 204) {
    return {} as T
  }

  return response.json() as Promise<T>
}

export const apiClient = {
  get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return request<T>(endpoint, { ...options, method: 'GET' })
  },
  post<T>(endpoint: string, body?: any, options?: RequestOptions): Promise<T> {
    return request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  },
  patch<T>(endpoint: string, body?: any, options?: RequestOptions): Promise<T> {
    return request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  },
  delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return request<T>(endpoint, { ...options, method: 'DELETE' })
  },
}
