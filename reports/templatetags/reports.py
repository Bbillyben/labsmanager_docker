from django import template

register = template.Library()

@register.filter(name='dict_key')
def dict_key(d, k):
    '''Returns the given key from a dictionary.'''
    if k in d:
        return d[k]
    return None