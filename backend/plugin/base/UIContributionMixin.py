"""Declarative React contributions from an active plugin."""


class UIContributionMixin:
    """Opt in to the shared, server validated UI contribution slots."""

    UI_CONTRIBUTIONS = ()

    class MixinMeta:
        MIXIN_NAME = "UI contributions"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_mixin("uicontribution", True, __class__)
