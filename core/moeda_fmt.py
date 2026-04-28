"""Formatação e leitura de valores em Real (pt-BR): milhar com ponto, decimais com vírgula (ex.: 5.200,00)."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django import forms


def format_decimal_br_moeda(d: Decimal, *, decimal_places: int = 2) -> str:
    """Formata Decimal no padrão brasileiro (1.234,56), sem prefixo R$."""
    q = Decimal('1').scaleb(-decimal_places)
    d = d.quantize(q)
    neg = d < 0
    d = abs(d)
    whole = int(d)
    frac = int((d - Decimal(whole)) * Decimal(10**decimal_places))
    if whole == 0:
        intp = '0'
    else:
        s = str(whole)
        blocks: list[str] = []
        while s:
            blocks.append(s[-3:])
            s = s[:-3]
        intp = '.'.join(reversed(blocks))
    frac_s = str(frac).zfill(decimal_places)
    out = f'{intp},{frac_s}'
    return ('-' if neg else '') + out


def parse_valor_moeda_br(raw) -> Decimal | None:
    """
    Aceita valor normalizado pelo JS (1234.56), formato BR (1.234,56) ou só vírgula decimal.
    Retorna None se vazio ou zero (comportamento alinhado a campos opcionais de obra).
    """
    if raw is None:
        return None
    s = (
        str(raw)
        .strip()
        .replace(' ', '')
        .replace('R$', '')
        .replace('r$', '')
    )
    if not s:
        return None
    if s in ('-', ',', '.'):
        raise forms.ValidationError('Informe um valor numérico válido.')
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    else:
        if s.count('.') > 1:
            s = s.replace('.', '')
    try:
        d = Decimal(s)
    except InvalidOperation as e:
        raise forms.ValidationError('Informe um valor numérico válido.') from e
    if d < 0:
        raise forms.ValidationError('O valor não pode ser negativo.')
    if d == 0:
        return None
    if abs(d) >= Decimal('1e15'):
        raise forms.ValidationError('Valor inválido.')
    return d.quantize(Decimal('0.01'))


def parse_valor_moeda_obrigatorio(raw, *, msg_vazio: str = 'Informe um valor maior que zero.') -> Decimal:
    """Para lançamentos que exigem valor > 0."""
    try:
        d = parse_valor_moeda_br(raw)
    except forms.ValidationError:
        raise
    if d is None:
        raise forms.ValidationError(msg_vazio)
    return d
