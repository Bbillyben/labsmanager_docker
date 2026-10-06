class SearchPluginMixin:
    """Contribute Search Providers through the existing active plugin registry."""

    class MixinMeta:
        MIXIN_NAME = "Search"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_mixin("search", True, __class__)

    def get_search_providers(self, user):
        return ()
