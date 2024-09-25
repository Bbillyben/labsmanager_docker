"""Plugin mixin class for Calendar Event."""
from plugin.helpers import MixinImplementationError
from django.conf import settings
from settings.accessor import get_global_setting
import logging
logger = logging.getLogger('labsmanager')

class CalendarEventMixin:
    '''
    Mixin to add event to calendar view
    event can be linked to resource
    use __class__.get_current_resources(request) to get resources used in the current view
    '''
    FILTERS={}
    '''
        if implemented, will add some filter to the calendar, override __class__.get_filters() to leverage behaviors
        filters will only have effect after all other builtin filters
        
    '''
    class MixinMeta:
        """Meta options for this mixin."""
        MIXIN_NAME = 'CalendarEvent'
        
    def __init__(self):
        """Register mixin."""
        super().__init__()
        self.add_mixin('calendarevent', self.has_extended_meth, __class__)
        
    @classmethod
    def get_event(cls, request, event_list):
        """
        Add extra events to full calendar 
        This method has to be overriden if not overrided, the mixin is not enabled on the plugin.
        
        
        Args : 
            request : the request object from labcalendar. request.GET contain information about date slots, calendar filters

                request as in POST dict : 
                filters from main calendar
                * type : type of leave.model.leave_type
                * type_exact : if has to filter on tree 
                * emp_status : employee status (staff.model.employee_type)
                * team : team from staff.model.team
                * showResEventRadio : whether only resource with event are printed (false, true, only_today)
                * view : the current view (! not update on view change, only when event resource are reloaded)
                * start : the start date of the time frame
                * end : the end date of the time frame
                * timezone
                * settings : the setting object of the calendar, which contain :
                    * cal_type : depict what type of calendar the request coming from (main, team, employee)
                * resources : the current resources !!! may not be up to date prefer __class__.get_current_resources(request) for more reliable data
           
            event_list : the list of events that will be send to calendar. Has to be in full calendar format, eg :
                {
                    'title':'the title', # if not set as labmanager event, will be printed as is / best to get one for non backgroud event
                    'start':start_date,
                    'end': end_date,
                    'desc': description,# if description is provided, a popup could be opened, could be html
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
   
    @classmethod
    def filter_queryset(cls, queryset, filters_data):
        '''
        method to add filtering on events (all events from labsmanager process)
        Args : 
           * queryset : the queryset comming from the labsmanager filtering process
           * filters_data : dict containing the filters
        '''
        return queryset
    
        
        
    def activate(self):
        ''' when mixin is activated and plugin activated call activate.
        usefull to preparing data if reaquired (ie load data source)'''
        pass
    def desactivate(self):
        ''' when mixin is desactivated and plugin activated call desactivate.
        usefull to unpreparing data if required (ie load data source)'''
        pass
    
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
    def get_current_resources(cls, request):
        ''' 
        retrieve the resources printed in the current calendar from request

        '''
        from staff.apiviews import EmployeeViewSet
        from django.http import QueryDict
        if not hasattr(request, "data") or request.data is None:
            if hasattr(request, "POST"):
                request.data = QueryDict(request.POST.urlencode())
                request.query_params = QueryDict(request.POST.urlencode())
            elif hasattr(request, "GET"):
                request.data = QueryDict(request.GET.urlencode())
                request.query_params = QueryDict(request.GET.urlencode())
        res = EmployeeViewSet.select_ressource_from_request(request)
        return res
        
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