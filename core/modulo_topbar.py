import re

from django.http import HttpRequest


def titulo_modulo_topbar(request: HttpRequest) -> str:
    """
    Rótulo do módulo atual para o topbar, alinhado às áreas do menu lateral.
    """
    path = request.path or ''

    if path.startswith('/admin'):
        return 'Administração'

    if '/empresa/' not in path:
        if '/selecionar-empresa' in path:
            return 'Selecionar empresa'
        if '/trocar-empresa' in path:
            return 'Trocar empresa'
        if path.startswith('/accounts/'):
            return 'Conta'
        if '/usuarios/perfil' in path:
            return 'Meu perfil'
        if path.startswith('/usuarios/'):
            return 'Conta'
        return 'Genesis ERP'

    if re.search(r'/empresa/\d+/apontamento(/|$)', path):
        return 'Apontamento'
    if re.search(r'/empresa/\d+/rh/gestao(/|$)', path):
        return 'Gestão RH'
    if '/locais-trabalho/mapa/' in path:
        return 'Mapa de Trabalho'
    if '/locais-trabalho/' in path:
        return 'Locais de Trabalho'
    if re.search(r'/empresa/\d+/rh(/|$)', path):
        return 'Recursos Humanos'
    if re.search(r'/empresa/\d+/auditoria(/|$)', path):
        return 'Auditoria'
    if re.search(r'/empresa/\d+/fornecedores(/|$)', path):
        return 'Fornecedores'
    if re.search(r'/empresa/\d+/clientes(/|$)', path):
        return 'Clientes'
    if re.search(r'/empresa/\d+/obras(/|$)', path):
        return 'Obras'
    if re.search(r'/empresa/\d+/local(/|$)', path):
        return 'Locais'
    if re.search(r'/empresa/\d+/preferencias(/|$)', path):
        return 'Preferências'
    if re.search(r'/empresa/\d+/usuarios(/|$)', path):
        return 'Conta'
    if re.match(r'^/empresa/\d+/?$', path):
        return 'Início'
    return 'Início'
