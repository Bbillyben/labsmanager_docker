import { getCsrfToken } from './csrf'
import { ApiError } from './errors'

type UnauthorizedListener = () => void
const unauthorizedListeners = new Set<UnauthorizedListener>()
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS', 'TRACE'])

export function subscribeToUnauthorized(listener: UnauthorizedListener) {
  unauthorizedListeners.add(listener)
  return () => {
    unauthorizedListeners.delete(listener)
  }
}

async function readResponse(response: Response): Promise<unknown> {
  if (response.status === 204) return undefined
  const contentType = response.headers.get('content-type') ?? ''
  return contentType.includes('application/json') ? response.json() : undefined
}

export async function apiRequest<T>(url: string, init: RequestInit = {}): Promise<T> {
  if (!url.startsWith('/') || url.startsWith('//')) {
    throw new TypeError('API URLs must be relative to the current origin')
  }

  const method = (init.method ?? 'GET').toUpperCase()
  const headers = new Headers(init.headers)
  if (!SAFE_METHODS.has(method)) {
    const csrfToken = getCsrfToken()
    if (csrfToken) headers.set('X-CSRFToken', csrfToken)
  }

  const response = await fetch(url, { ...init, method, headers, credentials: 'include' })
  const payload = await readResponse(response)
  if (!response.ok) {
    if (response.status === 401) unauthorizedListeners.forEach((listener) => listener())
    throw new ApiError(response.status, payload)
  }
  return payload as T
}
