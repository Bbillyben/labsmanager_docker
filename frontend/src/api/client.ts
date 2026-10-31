import { getCsrfToken } from './csrf'
import { ApiError } from './errors'

type UnauthorizedListener = () => void
const unauthorizedListeners = new Set<UnauthorizedListener>()
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS', 'TRACE'])

/** Notify a caller about future HTTP 401 responses; returns its unsubscribe. */
export function subscribeToUnauthorized(listener: UnauthorizedListener) {
  unauthorizedListeners.add(listener)
  return () => {
    unauthorizedListeners.delete(listener)
  }
}

/** Decode an HTTP response and raise an API error on failure. */
async function readResponse(response: Response): Promise<unknown> {
  if (response.status === 204) return undefined
  const contentType = response.headers.get('content-type') ?? ''
  return contentType.includes('application/json') ? response.json() : undefined
}

/** Send a same-origin API request with session credentials and CSRF handling.
 *
 * Unsafe methods receive the current CSRF token when one is available. A 401
 * notifies subscribers, and any non-success response throws `ApiError`.
 *
 * @param url - Root-relative URL on the current origin.
 * @param init - Fetch options; method defaults to GET.
 * @param responseType - Read successful payload as JSON or text.
 * @returns Parsed response, or `undefined` for HTTP 204.
 */
export async function apiRequest<T>(url: string, init: RequestInit = {}, responseType: 'json' | 'text' = 'json'): Promise<T> {
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
  const payload = response.ok && responseType === 'text' ? await response.text() : await readResponse(response)
  if (!response.ok) {
    if (response.status === 401) unauthorizedListeners.forEach((listener) => listener())
    throw new ApiError(response.status, payload)
  }
  return payload as T
}

/** Download a same-origin file while preserving an optional response filename.
 *
 * The filename comes from `Content-Disposition` when available. Non-success
 * responses throw `ApiError` and 401 responses notify auth subscribers.
 */
export async function apiFileRequest(url: string, init: RequestInit): Promise<{ blob: Blob; filename: string | null }> {
  if (!url.startsWith('/') || url.startsWith('//')) throw new TypeError('API URLs must be relative to the current origin')
  const headers = new Headers(init.headers)
  const csrfToken = getCsrfToken()
  if (csrfToken) headers.set('X-CSRFToken', csrfToken)
  const response = await fetch(url, { ...init, headers, credentials: 'include' })
  if (!response.ok) {
    if (response.status === 401) unauthorizedListeners.forEach((listener) => listener())
    throw new ApiError(response.status, await readResponse(response))
  }
  const disposition = response.headers.get('content-disposition') ?? ''
  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1]
  const quoted = disposition.match(/filename="([^"]+)"/i)?.[1]
  const filename = encoded ? decodeURIComponent(encoded) : quoted ?? null
  return { blob: await response.blob(), filename }
}
