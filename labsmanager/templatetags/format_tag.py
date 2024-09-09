from django import template
from django.utils.safestring import mark_safe
from django.core.validators import validate_email

from settings.models import LMUserSetting
import urllib.parse

register = template.Library()

@register.simple_tag()
def contact_info(info, user):
    if info.info.type == "mail":
        try:
            validate_email(info.value)
            return mark_safe(f'<a href="mailto:{info.value}">{info.value}</a>')
        except:
            return info.value
    if info.info.type == "tel":
        return mark_safe(f'<a href="tel:{info.value}">{info.value}</a>')
    if info.info.type == "link":
        return mark_safe(f'<a href="{info.value}">{info.value}</a>')
    if info.info.type == "addr":
        setMap = LMUserSetting.get_setting("MAP_PROVIDER", user=user)
        encoded_address = urllib.parse.quote_plus(info.value)
        match setMap:
            case "gmap":
                base_url = "https://www.google.com/maps/search/?api=1&query="
            case "opensm":
                base_url = "https://www.openstreetmap.org/search?query="
            case _:
                return info.value
        ref = base_url + encoded_address
        return mark_safe(f'<a href="{ref}" target="blank">{info.value}</a>')
    return info.value