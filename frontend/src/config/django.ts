const configuredOrigin = import.meta.env.VITE_DJANGO_PUBLIC_URL?.trim();

/** Build a URL to a Django-served route using the configured base path. */
export function getDjangoUrl(path: string) {
  if (!path.startsWith('/') || path.startsWith('//')) {
    throw new TypeError('Django paths must be root-relative');
  }
  if (!configuredOrigin) return path;
  return new URL(path, `${configuredOrigin.replace(/\/$/, '')}/`).toString();
}
