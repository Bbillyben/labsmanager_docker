from decimal import Decimal
from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe


import math
import uuid
register = template.Library()


@register.simple_tag
def setvar(val=None):
  return val

@register.simple_tag(takes_context=True)
def isUserTeamLeader(context, dynvarname):
    """ Returns the value of dynvarname into the context """
    return context.get("user_"+str(dynvarname), None)


@register.simple_tag(takes_context=True)
def quotityFormat(context, dynvarname):
    """ Returns the value of dynvarname into the context """
    if isinstance(dynvarname, str) and not dynvarname.isnumeric():
         html="-"
    elif dynvarname != None:
        val = "{0:.0%}".format(dynvarname)
        if dynvarname > 1:
            html="<div class='warning-quotity'>"+val+"</div>"
        else :
            html="<div class=''>"+val+"</div>"
    else:
        html="-"
        
    return mark_safe(html)

@register.simple_tag(takes_context=True)
def moneyFormat(context, dynvarname):
    """ Returns the value of dynvarname into the context """
    # if dynvarname != None and (type(dynvarname) == int or type(dynvarname)==float or type(dynvarname)==Decimal) and math.isnan(dynvarname)==False :
    #     val =  "{:0,.0f}€".format(dynvarname).replace(',', ' ') 
    # else:
    try:
        varF = float(dynvarname)
        val =  "{:0,.0f}€".format(varF).replace(',', ' ') 
    except:        
        val="-" 
    return mark_safe(val)


@register.simple_tag(takes_context=True)
def etpFormat(context, dynvarname):
    """ Returns the value of dynvarname into the context """
    if dynvarname != None:
        val =  "{:.1f}".format(dynvarname)
    else:
         val="-" 
    return mark_safe(val)

import re

@register.simple_tag(name='makeId')
def makeID(dynvarname):
    """ Returns the value of dynvarname into the context """
    # strV=str(dynvarname).replace(" ", "_")
    return re.sub("[^a-zA-Z0-9]", "", str(dynvarname), count=0, flags=0)
    #return strV.upper()

@register.filter(name='nospace')
def nospace(value):
    """ Returns the value of dynvarname with wpace replaced by - """
    return value.replace(' ', '-')
    

@register.simple_tag(name='unikId')
def unikId():
    """ Returns the value of dynvarname into the context """
    return uuid.uuid4().hex



from project.models import Project
@register.simple_tag()
def setting_object(key, *args, **kwargs):
    """Return a setting object speciifed by the given key.
    (Or return None if the setting does not exist)
    if a user-setting was requested return that
    """
    from settings.models import LMUserSetting, LabsManagerSetting, LMProjectSetting
    from plugin.models import PluginSetting, PluginConfig
    from plugin import LabManagerPlugin

    if 'user' in kwargs:
        return LMUserSetting.get_setting_object(key, user=kwargs['user'])
    
    if 'project' in kwargs:
        # try:
        proj = Project.objects.get(pk=kwargs['project'])
        return LMProjectSetting.get_setting_object(key, project=proj)
        # except:
        #     return None
    if 'plugin' in kwargs:
        plg = kwargs['plugin']
        if issubclass(plg.__class__, LabManagerPlugin):
            try:
                plg = plg.plugin_config()
            except PluginConfig.DoesNotExist:
                return None

        return PluginSetting.get_setting_object(
            key, plugin=plg
        )
    return LabsManagerSetting.get_setting_object(key)
    # else:
    #     raise Warning("User Is not set for User settings display")

@register.simple_tag()
def settings_value(key, *args, **kwargs):
    from settings.models import LMUserSetting, LabsManagerSetting, LMProjectSetting
    """Return a settings value specified by the given key."""
    if 'user' in kwargs:
        if not kwargs['user'] or (kwargs['user'] and kwargs['user'].is_authenticated is False):
            return LMUserSetting.get_setting(key)
        return LMUserSetting.get_setting(key, user=kwargs['user'])
    if 'project' in kwargs:
        if not kwargs['project'] :
            return LMUserSetting.get_setting(key)
        return LMProjectSetting.get_setting(key, project=kwargs['project'])

    return LabsManagerSetting.get_setting(key)


@register.simple_tag()
def get_filter_lists( *args, **kwargs):
    from labsmanager.views import get_filters_lists
    return get_filters_lists(None, safe=False)

@register.simple_tag()
def get_faIcon(*args, **kwargs):
    from faicon import widgets
    icon=args[0]
    return icon.icon_html()

@register.filter
def addstr(arg1, arg2):
    return str(arg1) + str(arg2)


@register.simple_tag(takes_context=True)
def extractArgs(context, key):
   if key in context:
       return context[key]
   return None


@register.filter
def is_in_leavelist(d, d_list):   
    for ds in d_list:
        if d>=ds.start_date and d<=ds.end_date:
            return True
    return False

# return a  range for a given value, for loop with increment
@register.filter
def get_range(value):
    return range(value)

# define a filter list name
@register.simple_tag
def filter_name(type, sub_type=None):
    if sub_type is None:
        return type
    return f'{type}_{sub_type}'


from labsmanager.themes import LabTheme
from labsmanager import settings
from settings.models import LMUserSetting, LabsManagerSetting
import os

@register.simple_tag()
def get_color_theme(user):
    ctName = LMUserSetting.get_setting("LAB_THEME", user=user)
    ct = LabTheme.get_theme(ctName)
    cssPath = os.path.join("/",settings.STATIC_URL,'css', 'color-themes', ct + '.css')
    return cssPath

@register.simple_tag()
def get_color_theme_browser(request):
    if request.user and not request.user.is_anonymous:
        return get_color_theme(request.user)
    
    accept_header = request.META.get('HTTP_ACCEPT', '')
    if 'dark' in accept_header:
        ctName = "dark-reader"
    else:
        ctName = "default"
    ct = LabTheme.get_theme(ctName)
    cssPath = os.path.join("/",settings.STATIC_URL,'css', 'color-themes', ct + '.css')
    return cssPath