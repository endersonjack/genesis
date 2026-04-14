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


def _rest_segment(rest: str) -> str:
    p = (rest or '').lstrip('/').rstrip('/')
    if not p:
        return ''
    return p.split('/', 1)[0]


def modulo_permitido_para_usuario(rest: str, vinculo) -> tuple[bool, str]:
    """
    Controle de acesso por módulo (via vínculo usuário–empresa).

    Retorna (permitido, mensagem_erro).
    """
    seg = _rest_segment(rest)
    if not seg:
        return True, ''

    # Dashboard e recursos "globais" dentro do escopo da empresa.
    if seg in ('',):
        return True, ''

    # Módulos/rotas por prefixo (ver config/urls.py).
    if seg == 'rh':
        return bool(getattr(vinculo, 'rh', False)), 'Você não tem acesso ao módulo RH nesta empresa.'
    if seg == 'estoque':
        return bool(getattr(vinculo, 'estoque', False)), 'Você não tem acesso ao módulo Estoque nesta empresa.'
    if seg == 'clientes':
        return bool(getattr(vinculo, 'clientes', False)), 'Você não tem acesso ao módulo Clientes nesta empresa.'
    if seg == 'fornecedores':
        return bool(getattr(vinculo, 'fornecedores', False)), 'Você não tem acesso ao módulo Fornecedores nesta empresa.'
    if seg == 'local':
        return bool(getattr(vinculo, 'locais', False)), 'Você não tem acesso ao módulo Locais nesta empresa.'
    if seg == 'obras':
        return bool(getattr(vinculo, 'obras', False)), 'Você não tem acesso ao módulo Obras nesta empresa.'
    if seg == 'auditoria':
        return bool(getattr(vinculo, 'auditoria_total', False) or getattr(vinculo, 'auditoria_sua', False)), (
            'Você não tem acesso à Auditoria nesta empresa.'
        )
    if seg == 'preferencias':
        return bool(getattr(vinculo, 'editar_empresas', False)), (
            'Você não tem acesso para editar as preferências desta empresa.'
        )

    # Financeiro ainda não tem urls dedicadas; mantém neutro caso exista rota no futuro.
    return True, ''
