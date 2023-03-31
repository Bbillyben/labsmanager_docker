from decimal import Decimal
from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe


import math
import uuid
register = template.Library()

@register.simple_tag(takes_context=True)
def isUserTeamLeader(context, dynvarname):
    """ Returns the value of dynvarname into the context """
    return context.get("user_"+str(dynvarname), None)


@register.simple_tag(takes_context=True)
def quotityFormat(context, dynvarname):
    """ Returns the value of dynvarname into the context """
    
    if dynvarname != None:
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
    if dynvarname != None and (type(dynvarname) == int or type(dynvarname)==float or type(dynvarname)==Decimal) and math.isnan(dynvarname)==False :
        val =  "{:0,.0f}€".format(dynvarname).replace(',', ' ') 
    else:
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


@register.simple_tag(name='unikId')
def unikId():
    """ Returns the value of dynvarname into the context """
    return uuid.uuid4().hex




@register.simple_tag()
def setting_object(key, *args, **kwargs):
    """Return a setting object speciifed by the given key.
    (Or return None if the setting does not exist)
    if a user-setting was requested return that
    """
    from settings.models import LMUserSetting, LabsManagerSetting

    if 'user' in kwargs:
        return LMUserSetting.get_setting_object(key, user=kwargs['user'])
    
    return LabsManagerSetting.get_setting_object(key)
    # else:
    #     raise Warning("User Is not set for User settings display")

@register.simple_tag()
def get_filter_lists( *args, **kwargs):
    from labsmanager.views import get_filters_lists
    return get_filters_lists(None, safe=False)

@register.simple_tag()
def get_faIcon(*args, **kwargs):
    from faicon import widgets
    print(" get_faIcon")
    print(" - args :"+str(args))
    print(" - kwargs :"+str(kwargs))
    icon=args[0]
    # icon=widgets.parse_icon(str(obj.icon))
    # if isinstance(icon, widgets.Icon):
    #     return icon.icon_html()
    return icon.icon_html()