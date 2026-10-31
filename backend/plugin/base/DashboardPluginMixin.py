class DashboardPluginMixin:
    """Contribute dashboard definitions through the active plugin registry.

    Override either getter to return definitions for the supplied dashboard
    context. The dashboard registry validates contributed sources and widgets;
    an empty tuple contributes nothing.
    """

    class MixinMeta:
        MIXIN_NAME = "Dashboard"

    def __init__(self):
        super().__init__()
        self.add_mixin("dashboard", True, __class__)

    def get_dashboard_sources(self, context):
        """Return source definitions for the given dashboard context."""
        return ()

    def get_dashboard_widgets(self, context):
        """Return widget definitions for the given dashboard context."""
        return ()
