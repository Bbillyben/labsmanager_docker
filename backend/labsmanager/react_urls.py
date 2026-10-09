from urllib.parse import urljoin

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def react_public_url(path):
    """Resolve a path below the public React /app base."""
    base = settings.REACT_PUBLIC_URL.strip().rstrip("/")
    if not base:
        raise ImproperlyConfigured("REACT_PUBLIC_URL is required for React authentication links")
    return urljoin(f"{base}/", path.lstrip("/"))
