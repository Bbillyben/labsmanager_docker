"""Plugin mixin class for Calendar Event."""
from plugin.helpers import MixinImplementationError
from django.conf import settings
from settings.accessor import get_global_setting
import copy
import logging
logger = logging.getLogger('labsmanager')

class CalendarEventMixin:
    '''
    Mixin to add event to calendar view
    event can be linked to resource
    use __class__.get_current_resources(request) to get resources used in the current view
    '''
    FILTERS={}
    '''FILTERS 
        if implemented, will add some filter choices to main calendar page (not in employee nor team panels), 
        
        FILTERS={
            "TEST_CHOICES":{            # this will add a filter in main calendar
                                            # TEST_CHOICES in lower case (aka test_choices) will be used as filter name
                                            # filter value will be accissible through [plugin-slug]-test_choices
                "title":"Test Choices", # title prompted on the filter box
                "type":"select",        # could be "select" for a dropdown/select item, 
                                            #   "checkbox" for a bunch of checkboxes
                                            #   "radio" for a radio list
                                            #   "input-text" "input-color" for input type selectors, no choices required
                "choices":{             # dict of valid choices with pair value:name, value will be returned as filter value
                    "val1":"Value 1",
                    "val2":"Value 2",
                    ....
                "choices":"myClassMethod" // could be the string name of a **classmethod** as well
        },            
    }
    '''
    
    authorized_type=["select", "checkbox", "radio","input-text", "input-color",] # authorized type, corresponding to a specific template
    type_with_choices=["select", "checkbox", "radio",] # type that require choices
    
    class MixinMeta:
        """Meta options for this mixin."""
        MIXIN_NAME = 'CalendarEvent'
        
    def __init__(self):
        """Register mixin."""
        super().__init__()
        self.add_mixin('calendarevent', 'is_setting_enabled', __class__)
    
    def is_setting_enabled(cls):
       return get_global_setting('ENABLE_PLUGINS_CALENDAR')
    @classmethod
    def get_event(cls, request, event_list):
        """
        Add extra events to full calendar       
        
        Args : 
            request : the request object from labcalendar. request.GET contain information about date slots, calendar filters + filters from plugins 

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
        only filtering leave instance from 
        Args : 
           * queryset : the queryset comming from the labsmanager filtering process of leave instances
           * filters_data : dict containing the filters, including FILTERS value (under slug-filtername (lower case))
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
    
    @classmethod
    def get_filters(cls):
        '''
        method called by filter template to get filter definition should return the FILTERS copy with all choices in good shape and remove not allowed type
        '''
        return cls.build_filters()
    
    @classmethod
    def build_filters(cls):
        '''
        method to build a clean dict from FILTERS definition
        '''
        # copy only filters in authorized types
        build_filters = {k: v for k, v in cls.FILTERS.items() if v.get("type") in cls.authorized_type}
        key_to_pop=[]
        for filter, option in build_filters.items():
            if "choices" in option:
                vals = option["choices"]
                # check if choices is classmethod and execute it to get choices
                if isinstance(vals, str) and hasattr(cls, vals):
                    methode = getattr(cls, vals)
                    if callable(methode):
                        vals = methode()  # Exécute la méthode 
                        option["choices"] =vals
                # test if choices are well formed, i.e. alla value are not another dict
                if isinstance(vals, str) or not all(not isinstance(value, dict) for value in vals.values()):
                    logger.warning(f"Error for filters '{filter}' in {cls} in choices format")
                    key_to_pop.append(filter)
            elif option["type"] in cls.type_with_choices:
                logger.warning(f"Error for filters '{filter}' in {cls} missing choices")
                key_to_pop.append(filter) # no choices defined for filters with choice mandatory
                
        for key in key_to_pop: # remove key with unwanted format
            build_filters.pop(key)
        return build_filters
                
                