"""Plugin mixin class for Calendar Event."""
from plugin.helpers import MixinImplementationError
from django.conf import settings
from settings.accessor import get_global_setting
import logging
logger = logging.getLogger('labsmanager')

class CalendarEventMixin:
    '''
    Mixin to add event to calendar view customs event
    '''
    class MixinMeta:
        """Meta options for this mixin."""

        MIXIN_NAME = 'CalendarEvent'
        
    def __init__(self):
        """Register mixin."""
        super().__init__()

        self.add_mixin('calendarevent', 'has_extended_meth', __class__)
        
    @classmethod
    def _activate_mixin(cls, registry, plugins, *args, **kwargs):
        """Activate plugin calendarevent.
        """
        logger.debug('Activating plugin calendarevent')
        if settings.PLUGIN_TESTING or get_global_setting('ENABLE_PLUGINS_CALENDAR'):
            for _key, plugin in plugins:
                print(f" - activating :  {plugin} : {plugin.mixin_enabled('calendarevent')}")
                if plugin.mixin_enabled('calendarevent') and plugin.is_active():
                    plugin.activate()


    @classmethod
    def _deactivate_mixin(cls, registry, **kwargs):
        """Deactivate all plugin settcalendareventings."""
        logger.debug('Deactivating plugin calendarevent')

    
    @classmethod
    def get_event(cls, request, event_list):
        """
        This method has to be overriden
        append to 'event_list' events we want to add in calendar view 
        if not overrided, the mixin is not enabled on the plugin.
        request: the request object from labcalendar
            request.GET contain information about date slots, calendar filters
        
        event should be in fullcalendar format
        
        """
        raise MixinImplementationError('CalendarEventMixin : get_event should be overriden')

    def activate(self):
        ''' launch when activated for preparing if needed '''
    @property
    def has_extended_meth(self):
        """
        Check if the get_event method has been overriden. if not => error of implementation
        """
        method_name = 'get_event'
        derived_method = getattr(self.__class__, method_name, None).__func__
        original_method = getattr(CalendarEventMixin, method_name, None).__func__

        # Si la méthode de la classe dérivée est différente de celle du mixin, elle a été surchargée
        return derived_method != original_method