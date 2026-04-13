"""
Página hub de relatórios do RH (presets via export da busca + link para busca manual).
"""

from django.shortcuts import render

from .base import _empresa_ativa_or_redirect


def relatorios_rh(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para acessar os relatórios de RH.',
    )
    if redirect_response:
        return redirect_response

    return render(request, 'rh/relatorios.html', {})
