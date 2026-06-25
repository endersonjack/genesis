"""
Página hub de relatórios do RH (presets via export da busca + link para busca manual).
"""

from django.shortcuts import render

from local.models import LocalTrabalhoAtivo

from ..models import Lotacao
from .base import _empresa_ativa_or_redirect


def relatorios_rh(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para acessar os relatórios de RH.',
    )
    if redirect_response:
        return redirect_response

    lotacoes = Lotacao.objects.filter(empresa=empresa_ativa).order_by('nome')
    locais_trabalho = [
        ativo.local
        for ativo in LocalTrabalhoAtivo.objects.filter(empresa=empresa_ativa)
        .select_related('local')
        .order_by('local__nome')
    ]
    return render(
        request,
        'rh/relatorios.html',
        {
            'lotacoes': lotacoes,
            'locais_trabalho': locais_trabalho,
        },
    )
