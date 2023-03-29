from django.contrib import admin

from faicon import widgets

class GenericInfoTypeAdmin(admin.ModelAdmin):
    list_display = ( 'name', 'get_icon',)
    
    @admin.display(description='Icon')
    def get_icon(self, obj):
        icon=widgets.parse_icon(str(obj.icon))
        if isinstance(icon, widgets.Icon):
            return icon.icon_html()
        return obj.icon
    class Media:
        css = {
            'all':('/static/fontawesome/css/all.css','/static/css/adminsmall.css',), 
        }