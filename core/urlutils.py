import re
from typing import Optional

from django.shortcuts import redirect
from django.urls import reverse

# Após trocar de empresa, não reutilizar o caminho se ele apontar para um recurso
# identificado por PK (ou competência/falta) que é exclusivo da empresa anterior;
# caso contrário o utilizador cai em 404 ou no registo errado.
_EMPRESA_SWAP_DASHBOARD_REST_PATTERNS = tuple(
    re.compile(p)
    for p in (
        r'^/rh/funcionarios/\d+',
        r'^/rh/faltas/funcionario/\d+',
        r'^/rh/faltas/competencia/\d+',
        r'^/rh/lembretes/\d+/',
        r'^/rh/cargos/\d+/',
        r'^/rh/lotacoes/\d+/',
        r'^/rh/gestao/competencias/\d+/\d+/',
        r'^/rh/gestao/competencias/\d+/editar/',
        r'^/rh/gestao/competencias/\d+/excluir/',
        r'^/rh/gestao/competencias/\d+/vt/',
        r'^/rh/gestao/competencias/\d+/cesta-basica/',
        r'^/rh/gestao/vt/\d+',
        r'^/rh/gestao/vt/tabela/\d+',
        r'^/rh/gestao/vt/itens/\d+',
        r'^/rh/gestao/cesta-basica/\d+',
        r'^/rh/gestao/cesta-basica/itens/\d+',
        r'^/local/\d+/',
        r'^/fornecedores/\d+',
        r'^/clientes/\d+',
        r'^/obras/\d+',
        r'^/estoque/categorias-itens/\d+',
        r'^/estoque/categorias-itens/modal/\d+',
        r'^/estoque/categorias-ferramentas/\d+',
        r'^/estoque/categorias-ferramentas/modal/\d+',
        r'^/estoque/unidades-medida/\d+',
        r'^/estoque/unidades-medida/modal/\d+',
        r'^/estoque/itens/modal/\d+',
        r'^/estoque/itens/\d+/imagens/\d+/excluir/',
        r'^/estoque/itens/\d+',
        r'^/estoque/requisicoes/\d+',
    )
)


def _empresa_swap_should_use_dashboard_only(rest: str) -> bool:
    if not rest or rest == '/':
        return False
    if not rest.startswith('/'):
        rest = '/' + rest
    return any(p.search(rest) for p in _EMPRESA_SWAP_DASHBOARD_REST_PATTERNS)


def reverse_empresa(request, viewname, args=None, kwargs=None):
    """
    reverse() com empresa_id obtido de request.empresa_ativa (rotas com prefixo empresa/<id>/).
    """
    empresa = getattr(request, 'empresa_ativa', None)
    if empresa is None:
        raise ValueError('reverse_empresa requer request.empresa_ativa')
    kw = dict(kwargs or {})
    kw['empresa_id'] = empresa.pk
    return reverse(viewname, args=args or (), kwargs=kw)


def redirect_empresa(request, viewname, args=None, kwargs=None, **url_kwargs):
    """
    redirect(reverse_empresa(...)) ou atalho redirect_empresa(request, 'name', kwargs={'pk': 1}).
    Aceita também redirect_empresa(request, 'name', pk=1) (mesclado em kwargs).
    """
    kw = dict(kwargs or {})
    kw.update(url_kwargs)
    return redirect(reverse_empresa(request, viewname, args=args, kwargs=kw or None))


def is_safe_internal_path(path: str) -> bool:
    """Evita open redirect: apenas caminhos relativos ao site."""
    if not path or not path.startswith('/'):
        return False
    if path.startswith('//'):
        return False
    if '..' in path:
        return False
    return True


def build_url_after_empresa_swap(path: str, new_empresa_id: int) -> Optional[str]:
    """
    Troca o segmento /empresa/<id>/ pelo novo id, mantendo o restante do caminho
    quando for seguro (listagens, dashboard, etc.).

    Se o caminho apontar para um recurso escopado por empresa (detalhe por PK,
    competência por id, tabelas VT/Cesta, etc.), devolve a URL do dashboard da
    nova empresa para evitar 404 ao manter o mesmo PK noutro tenant.
    """
    if not is_safe_internal_path(path):
        return None
    m = re.match(r'^/empresa/\d+(.*)$', path)
    if not m:
        return None
    rest = m.group(1)
    if rest == '':
        rest = '/'
    if _empresa_swap_should_use_dashboard_only(rest):
        return f'/empresa/{new_empresa_id}/'
    return f'/empresa/{new_empresa_id}{rest}'
