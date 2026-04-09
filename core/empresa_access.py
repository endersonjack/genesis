"""
Regras de acesso por vínculo usuário–empresa (ex.: usuário somente apontador).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from usuarios.models import UsuarioEmpresa


def usuario_e_so_apontador(usuario, vinculo: UsuarioEmpresa) -> bool:
    """
    Apontador «puro»: tem o flag apontador nesta empresa, mas não é admin da empresa
    nem superuser. Esse perfil fica restrito ao módulo Apontamento + rotas de locais.
    """
    if usuario.is_superuser:
        return False
    if vinculo.admin_empresa:
        return False
    return bool(vinculo.apontador)


def empresa_url_rest(path: str, empresa_id: int) -> str:
    """Parte do path após /empresa/<id>/ (sem barra inicial)."""
    prefix = f'/empresa/{int(empresa_id)}/'
    if not path.startswith(prefix):
        return ''
    return path[len(prefix) :]


def path_permitido_para_so_apontador(rest: str) -> bool:
    """
    Rotas permitidas para o apontador exclusivo, relativas a /empresa/<id>/.

    Inclui: apontamento, local (Locais), rh/locais-trabalho (inclui mapa e board),
    e a página HTMX de trocar empresa mantendo o prefixo da empresa.
    """
    if not rest or rest.strip() == '':
        return False
    p = rest.rstrip('/')
    if p.startswith('apontamento'):
        return p == 'apontamento' or p.startswith('apontamento/')
    if p == 'local' or p.startswith('local/'):
        return True
    if p.startswith('rh/locais-trabalho'):
        return p == 'rh/locais-trabalho' or p.startswith('rh/locais-trabalho/')
    if p == 'usuarios/trocar-empresa' or p.startswith('usuarios/trocar-empresa/'):
        return True
    return False
