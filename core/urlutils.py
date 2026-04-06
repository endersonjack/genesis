import re
from typing import Optional

from django.shortcuts import redirect
from django.urls import reverse


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
    Troca o segmento /empresa/<id>/ pelo novo id, mantendo o restante do caminho.
    Ex.: /empresa/5/rh/foo -> /empresa/7/rh/foo
    Retorna None se o path não for uma rota sob /empresa/<id>/.
    """
    if not is_safe_internal_path(path):
        return None
    m = re.match(r'^/empresa/\d+(.*)$', path)
    if not m:
        return None
    rest = m.group(1)
    if rest == '':
        rest = '/'
    return f'/empresa/{new_empresa_id}{rest}'
