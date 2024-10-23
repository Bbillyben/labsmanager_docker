
import logging

from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError

from settings.accessor import get_global_setting
from plugin.helpers import MixinImplementationError

logger = logging.getLogger('labsmanager')

class ReportMixin:
    '''
    Mixin to add context data to reports  

    '''
    
    class MixinMeta:
        """Meta options for this mixin."""
        MIXIN_NAME = 'ReportMixin'
        
    def __init__(self):
        """Register mixin."""
        super().__init__()
        self.add_mixin('report', True, __class__)
        
    def add_report_data(self, current_report, request, context):
        """Add extra context to the provided report instance.

        Args:
            current_report: The report instance to add context to
            model_instance: The model instance which initiated the report generation
            request: The request object which initiated the report generation
            context: The context dictionary to add to
        """
        pass
    
    @classmethod
    def _activate_mixin(cls, registry, plugins, *args, **kwargs):
        """Activate schedules from plugins with the ScheduleMixin."""
        logger.debug('Activating plugin Report')