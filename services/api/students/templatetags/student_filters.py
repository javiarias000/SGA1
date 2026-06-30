from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if dictionary is None:
        return None
    return dictionary.get(key, 0)

@register.filter
def split(value, arg):
    return value.split(arg)
