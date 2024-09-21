from django.utils.translation import gettext_lazy as _

from plugin import LabManagerPlugin
from plugin.base import SettingMixin

from labsmanager.validators import RGBColorValidator

class FrenchHollidayPlugin(SettingMixin, LabManagerPlugin):
    NAME = 'FrenchHollidayPlugin'
    SLUG = 'frenchholliday'
    TITLE = _('French Hollyday Agenda')
    AUTHOR = _('LabsManager contributors')
    DESCRIPTION = _('Display french vacation in agenda view')
    VERSION = '1.0.0'
    SETTINGS = {
        'FHP_COLOR': {
            'name': _('Background Color'),
            'description': _(''),
            'default': "#c9e0cf",
            'validator': RGBColorValidator,
        },
     }