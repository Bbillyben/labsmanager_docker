const CSRF_COOKIE_NAME = 'csrftoken'

/** Read the current CSRF token used by unsafe API requests. */
export function getCsrfToken(): string | undefined {
  const prefix = `${CSRF_COOKIE_NAME}=`
  const cookie = document.cookie.split(';').map((part) => part.trim()).find((part) => part.startsWith(prefix))
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : undefined
}
