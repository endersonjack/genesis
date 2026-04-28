"""Filtros de exibição monetária em Real (pt-BR)."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django import template

from core.moeda_fmt import format_decimal_br_moeda

register = template.Library()


@register.filter(name='moeda_br')
def moeda_br(value, decimal_places: str = '2') -> str:
    """
    Número no padrão 5.200,00 (sem R$).
    Uso: {{ valor|moeda_br }} ou {{ valor|moeda_br:4 }}
    """
    if value is None or value == '':
        return '—'
    try:
        places = int(decimal_places)
    except (TypeError, ValueError):
        places = 2
    if places < 0:
        places = 2
    try:
        d = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return '—'
    return format_decimal_br_moeda(d, decimal_places=places)
