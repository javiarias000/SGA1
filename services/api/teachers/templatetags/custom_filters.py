from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Obtiene el valor de un diccionario por clave"""
    if dictionary is None:
        return None
    return dictionary.get(key, 0)  # Devuelve 0 si no existe
