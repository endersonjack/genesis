from __future__ import annotations

from django import template

from ..requisicao_qty_fmt import fmt_quantidade_requisicao

register = template.Library()


@register.filter(name='qtd_requisicao_pdf')
def qtd_requisicao_pdf(value):
    return fmt_quantidade_requisicao(value)
