class SearchPluginMixin:
    """Contribute search providers through the active plugin registry.

    Providers are collected for the requesting user and validated by the
    global search registry. The default contributes none.
    """

    class MixinMeta:
        MIXIN_NAME = "Search"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_mixin("search", True, __class__)

    def get_search_providers(self, user):
        """Return provider instances available to the requesting user."""
        return ()
