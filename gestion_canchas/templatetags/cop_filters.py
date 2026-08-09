from django import template

register = template.Library()


@register.filter
def cop(value):
    """
    Formatea un número como pesos colombianos: 120000 -> $120.000
    Uso en template: {{ cancha.precio|cop }}
    """
    try:
        valor = int(value)
    except (TypeError, ValueError):
        return value
    return '${:,}'.format(valor).replace(',', '.')