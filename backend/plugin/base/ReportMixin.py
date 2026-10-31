
import logging

from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError

from settings.accessor import get_global_setting
from plugin.helpers import MixinImplementationError

logger = logging.getLogger('labsmanager')

class ReportMixin:
    """Let a plugin extend report rendering context.

    The report model calls ``add_report_data`` during generation. Overrides
    may add values to the supplied context for report templates.
    """
    
    class MixinMeta:
        """Meta options for this mixin."""
        MIXIN_NAME = 'ReportMixin'
        
    def __init__(self):
        """Register mixin."""
        super().__init__()
        self.add_mixin('report', True, __class__)
        
    def add_report_data(self, current_report, request, context):
        """Add plugin values to a report's rendering context.

        Args:
            current_report: Report instance being generated.
            request: Request that initiated report generation.
            context: Mutable template context to extend.
        """
        pass
    
    @classmethod
    def _activate_mixin(cls, registry, plugins, *args, **kwargs):
        """Activate schedules from plugins with the ScheduleMixin."""
        logger.debug('Activating plugin Report')