const CSRF_COOKIE_NAME = 'csrftoken'

export function getCsrfToken(): string | undefined {
  const prefix = `${CSRF_COOKIE_NAME}=`
  const cookie = document.cookie.split(';').map((part) => part.trim()).find((part) => part.startsWith(prefix))
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : undefined
}
