class DashboardPluginMixin:
    """Contribute dashboard definitions through the existing active plugin registry."""

    class MixinMeta:
        MIXIN_NAME = "Dashboard"

    def __init__(self):
        super().__init__()
        self.add_mixin("dashboard", True, __class__)

    def get_dashboard_sources(self, context):
        return ()

    def get_dashboard_widgets(self, context):
        return ()
