from labsmanager.utils import get_data_from_request

import logging
logger=logging.getLogger("labsmanager")

class CalendarPlulginMixin():
    def filter_queryset(self, queryset):
        data=get_data_from_request(self.request)        
        return self.plugin_filter_queryset(queryset, self.request.user, data)
                

    def plugin_filter_queryset(self, qset, user,  filters_data):
        from plugin import registry
        for plugin in registry.with_mixin("calendarevent", active=True):
           try:
               qset = plugin.filter_queryset(qset, user,  filters_data)
           except Exception as e:
               logger.warning(f"Error Filtering Leaves by plugin {plugin.name} : {e}")
        return qset