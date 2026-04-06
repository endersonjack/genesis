"""
Views de lotações do módulo RH.

Responsabilidades deste arquivo:
- listar lotações da empresa ativa
- criar nova lotação
- editar lotação
- excluir lotação

Observação:
- lotação substitui o conceito de "setor" no sistema
- usada em funcionários, filtros e relatórios
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.registry import audit_rh

from core.urlutils import redirect_empresa

from ..forms import LotacaoForm
from ..models import Lotacao
from .base import _empresa_ativa_or_redirect


# ==========================================================
# LISTA DE LOTAÇÕES
# ==========================================================
def lista_lotacoes(request):
    """
    Lista todas as lotações da empresa ativa.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para visualizar as lotações.'
    )
    if redirect_response:
        return redirect_response

    lotacoes = Lotacao.objects.filter(
        empresa=empresa_ativa
    ).order_by('nome')

    return render(
        request,
        'rh/lotacoes/lista.html',
        {
            'lotacoes': lotacoes,
        }
    )


# ==========================================================
# CRIAR LOTAÇÃO
# ==========================================================
def criar_lotacao(request):
    """
    Cria uma nova lotação.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de criar uma lotação.'
    )
    if redirect_response:
        return redirect_response

    if request.method == 'POST':
        form = LotacaoForm(request.POST, empresa_ativa=empresa_ativa)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa_ativa
            obj.save()

            audit_rh(
                request,
                'create',
                f'Lotação "{obj.nome}" criada.',
                {'lotacao_id': obj.pk},
            )
            messages.success(request, 'Lotação criada com sucesso.')
            return redirect_empresa(request, 'rh:lista_lotacoes')
    else:
        form = LotacaoForm(empresa_ativa=empresa_ativa)

    return render(
        request,
        'rh/lotacoes/form.html',
        {
            'form': form,
            'titulo': 'Nova Lotação',
        }
    )


# ==========================================================
# EDITAR LOTAÇÃO
# ==========================================================
def editar_lotacao(request, pk):
    """
    Edita uma lotação existente da empresa ativa.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de editar uma lotação.'
    )
    if redirect_response:
        return redirect_response

    lotacao = get_object_or_404(
        Lotacao,
        pk=pk,
        empresa=empresa_ativa,
    )

    if request.method == 'POST':
        form = LotacaoForm(
            request.POST,
            instance=lotacao,
            empresa_ativa=empresa_ativa,
        )
        if form.is_valid():
            salvo = form.save()
            audit_rh(
                request,
                'update',
                f'Lotação "{salvo.nome}" atualizada.',
                {'lotacao_id': salvo.pk},
            )
            messages.success(request, 'Lotação atualizada com sucesso.')
            return redirect_empresa(request, 'rh:lista_lotacoes')
    else:
        form = LotacaoForm(
            instance=lotacao,
            empresa_ativa=empresa_ativa,
        )

    return render(
        request,
        'rh/lotacoes/form.html',
        {
            'form': form,
            'lotacao': lotacao,
            'titulo': 'Editar Lotação',
        }
    )


# ==========================================================
# EXCLUIR LOTAÇÃO
# ==========================================================
def excluir_lotacao(request, pk):
    """
    Exclui uma lotação da empresa ativa.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de excluir uma lotação.'
    )
    if redirect_response:
        return redirect_response

    lotacao = get_object_or_404(
        Lotacao,
        pk=pk,
        empresa=empresa_ativa,
    )

    if request.method == 'POST':
        nome = lotacao.nome
        lid = lotacao.pk
        lotacao.delete()
        audit_rh(
            request,
            'delete',
            f'Lotação "{nome}" excluída.',
            {'lotacao_id': lid},
        )
        messages.success(request, 'Lotação excluída com sucesso.')
        return redirect_empresa(request, 'rh:lista_lotacoes')

    return render(
        request,
        'rh/lotacoes/excluir.html',
        {
            'lotacao': lotacao,
        }
    )