from labsmanager import settings
import os
from django.utils.translation import gettext_lazy as _
class LabTheme():
    default_color_theme = ('default', _('Default'))
    
    @classmethod
    def get_themes_choices(cls):
        """ Get all color themes from static folder """

        # Get files list from css/color-themes/ folder
        files_list = []
        for file in os.listdir("/"+settings.STATIC_COLOR_THEMES_DIR):
            files_list.append(os.path.splitext(file))

        # Get color themes choices (CSS sheets)
        choices = [(file_name.lower(), _(file_name.replace('-', ' ').title()))
                   for file_name, file_ext in files_list
                   if file_ext == '.css' and file_name.lower() != 'default']

        # Add default option as empty option
        choices.insert(0, cls.default_color_theme)

        return choices

    @classmethod
    def get_theme(cls, themeName):
        for ct in cls.get_themes_choices():
            if themeName == ct[0]:
                return themeName   
        return cls.default_color_theme[0]