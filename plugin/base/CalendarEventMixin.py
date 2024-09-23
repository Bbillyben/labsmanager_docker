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
                if plugin.mixin_enabled('calendarevent') and plugin.is_active():
                    plugin.activate()


    @classmethod
    def _deactivate_mixin(cls, registry, **kwargs):
        """Deactivate all plugin settcalendareventings."""
        logger.debug('Deactivating plugin calendarevent')
    
    @classmethod
    def get_event(cls, request, event_list):
        """
        Add extra events to full calendar 
        This method has to be overriden if not overrided, the mixin is not enabled on the plugin.
        
        
        Args : 
            request : the request object from labcalendar. request.GET contain information about date slots, calendar filters
            event_list : the list of events that will be send to calendar. Has to be in full calendar format, eg :
                {
                    'title':'the title', # if not set as labmanager event, will be printed as is
                    'start':start_date,
                    'end': end_date,
                    'desc': description,
                    'display': display, #see https://fullcalendar.io/docs/eventDisplay
                    'color': bg_color,
                    'className': "class-name",
                    # 'origin': 'lm', # add this one to be considered as labsmanager event! require resource, type, ....check api
                }
        
        extends event_list with new event :
              event_list.extends(newEvent)
              to not overwrite existing data
        """
        raise MixinImplementationError('CalendarEventMixin : get_event should be overriden')

    def activate(self):
        ''' when mixin is activated and plugin activated call activate.
        usefull to preparing data if reaquired (ie load data source)'''
        pass
    def desactivate(self):
        ''' when mixin is desactivated and plugin activated call desactivate.
        usefull to unpreparing data if required (ie load data source)'''
        pass
        
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