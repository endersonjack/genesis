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
