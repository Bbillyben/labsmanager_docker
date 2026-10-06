from django.utils.translation import gettext_lazy as _
class LabTheme():
    default_color_theme = ('light', _('Light'))

    @classmethod
    def get_themes_choices(cls):
        """Themes supported by the React interface."""
        return [('light', _('Light')), ('dark', _('Dark'))]

    @classmethod
    def get_theme(cls, themeName):
        """Keep the legacy template on its existing stylesheet for React theme IDs."""
        for ct in cls.get_themes_choices():
            if themeName == ct[0]:
                return 'default'
        return 'default'
