"""Formatação de exibição CPF/CNPJ (apenas dígitos no banco)."""


def display_cpf(digits: str) -> str:
    d = ''.join(c for c in (digits or '') if c.isdigit())[:11]
    if not d:
        return ''
    out = d[:3]
    if len(d) > 3:
        out += '.' + d[3:6]
    if len(d) > 6:
        out += '.' + d[6:9]
    if len(d) > 9:
        out += '-' + d[9:11]
    return out


def display_cnpj(digits: str) -> str:
    d = ''.join(c for c in (digits or '') if c.isdigit())[:14]
    if not d:
        return ''
    out = d[:2]
    if len(d) > 2:
        out += '.' + d[2:5]
    if len(d) > 5:
        out += '.' + d[5:8]
    if len(d) > 8:
        out += '/' + d[8:12]
    if len(d) > 12:
        out += '-' + d[12:14]
    return out


def display_cpf_cnpj(digits: str, tipo: str) -> str:
    d = ''.join(c for c in (digits or '') if c.isdigit())
    if not d:
        return ''
    if tipo == 'PF' or len(d) <= 11:
        return display_cpf(d)
    return display_cnpj(d)
