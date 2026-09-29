from django import template

register = template.Library()


@register.filter
def attr(obj, name):
    return getattr(obj, name, False)


@register.filter
def dictvalue(d, key):
    """Return d[key] safely — allows {{ my_dict|dictvalue:variable }} in templates."""
    try:
        return d[key]
    except (KeyError, TypeError):
        return 0


@register.filter
def pluralize(value, suffix='s'):
    try:
        return '' if int(value) == 1 else suffix
    except (ValueError, TypeError):
        return suffix
