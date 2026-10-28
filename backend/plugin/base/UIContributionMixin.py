"""Declarative React contributions from an active plugin."""


class UIContributionMixin:
    """Opt in to server validated UI slots.

    ``page`` declarations use slot ``plugin.page``; ``tab`` declarations use
    ``employee.detail.tabs``, ``team.detail.tabs`` and ``project.detail.tabs``. Both
    declare literal ``module`` (a Vite entry name), ``component`` (a named
    export), and ``api_version=1``. The plugin distributes its built manifest
    and assets in ``frontend/dist/``. Optional ``visible(request, context)``
    methods still control access; business APIs must check permissions too.
    Existing ``action`` and ``section`` declarations remain unchanged.

    A ``plugin.page`` may declare optional navigation metadata, for example::

        {"id": "agenda", "slot": "plugin.page", "type": "page", "label": "Agenda",
         "module": "main", "component": "Page", "api_version": 1,
         "navigation": {"location": "calendars", "labels": {"fr": "Agenda", "en": "Calendar"},
                        "icon": "calendar", "order": 0}}

    Navigation uses the page's existing route and optional ``visible`` method.
    Its metadata never loads the React module during discovery.
    """

    UI_CONTRIBUTIONS = ()

    class MixinMeta:
        MIXIN_NAME = "UI contributions"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_mixin("uicontribution", True, __class__)
