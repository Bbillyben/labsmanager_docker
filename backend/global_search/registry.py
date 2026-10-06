"""Single live registry for core and enabled-plugin Search Providers."""

import logging

from .contracts import SearchProvider
from .providers import CORE_PROVIDERS

logger = logging.getLogger("labsmanager")


class DuplicateProviderKey(ValueError):
    pass


class SearchRegistry:
    def __init__(self):
        self._core = {}

    def register(self, provider):
        if not isinstance(provider, SearchProvider) or not provider.key:
            raise ValueError("A SearchProvider needs a stable key")
        if provider.key in self._core:
            raise DuplicateProviderKey(provider.key)
        self._core[provider.key] = provider

    def unregister(self, key):
        return self._core.pop(key, None)

    def active(self, user):
        providers = dict(self._core)
        from plugin import registry as plugin_registry
        for plugin in plugin_registry.with_mixin("search", active=True):
            try:
                additions = tuple(plugin.get_search_providers(user))
                keys = [item.key for item in additions if isinstance(item, SearchProvider) and item.key]
                if len(keys) != len(additions) or len(keys) != len(set(keys)) or set(keys) & providers.keys():
                    raise DuplicateProviderKey("Invalid or colliding plugin Search Provider")
                providers.update((item.key, item) for item in additions)
            except Exception:
                logger.exception("Search providers from plugin %s were ignored", plugin)
        active = []
        for provider in providers.values():
            try:
                if provider.available(user):
                    active.append(provider)
            except Exception:
                logger.exception("Search provider %s was unavailable", provider.key)
        return tuple(active)

    def get(self, key, user):
        return next((provider for provider in self.active(user) if provider.key == key), None)


search_registry = SearchRegistry()
for provider in CORE_PROVIDERS:
    search_registry.register(provider)
