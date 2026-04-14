"""Formatação de quantidade na requisição (PDF + impressão HTML)."""

from __future__ import annotations

from decimal import Decimal


def fmt_quantidade_requisicao(q) -> str:
    try:
        v = Decimal(str(q))
    except Exception:
        v = Decimal('0')
    s = f'{v:.4f}'.rstrip('0').rstrip('.')
    return s if s else '0'
