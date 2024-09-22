from django.utils.translation import gettext_lazy as _

from plugin import LabManagerPlugin
from plugin.mixins import SettingsMixin

from labsmanager.validators import RGBColorValidator

class FrenchHollidayPlugin(SettingsMixin, LabManagerPlugin):
    NAME = 'FrenchHollidayPlugin'
    SLUG = 'frenchholliday'
    TITLE = _('French Hollyday Agenda')
    AUTHOR = _('LabsManager contributors/Bbillyben')
    DESCRIPTION = _('Display french vacation in agenda view')
    VERSION = '1.0.0'
    SETTINGS = {
        'FHP_COLOR': {
            'name': _('Background Color'),
            'description': _('background color of events'),
            'default': "#c9e0cf",
            'validator': [RGBColorValidator],
        },
        'FHP_BG': {
            'name': _('Send to BG'),
            'description': _('show as background'),
            'default': True,
            'validator': [bool],
        },
     }