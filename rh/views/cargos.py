"""
Views de cargos do módulo RH.

Responsabilidades deste arquivo:
- listar cargos da empresa ativa
- criar novo cargo
- editar cargo
- excluir cargo

Observação:
- cargos são usados no cadastro de funcionários, filtros e relatórios
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.urlutils import redirect_empresa

from ..forms import CargoForm
from ..models import Cargo
from .base import _empresa_ativa_or_redirect


# ==========================================================
# LISTA DE CARGOS
# ==========================================================
def lista_cargos(request):
    """
    Lista todos os cargos da empresa ativa.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para visualizar os cargos.'
    )
    if redirect_response:
        return redirect_response

    cargos = Cargo.objects.filter(
        empresa=empresa_ativa
    ).order_by('nome')

    return render(
        request,
        'rh/cargos/lista.html',
        {
            'cargos': cargos,
        }
    )


# ==========================================================
# CRIAR CARGO
# ==========================================================
def criar_cargo(request):
    """
    Cria um novo cargo.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de criar um cargo.'
    )
    if redirect_response:
        return redirect_response

    if request.method == 'POST':
        form = CargoForm(request.POST, empresa_ativa=empresa_ativa)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa_ativa
            obj.save()

            messages.success(request, 'Cargo criado com sucesso.')
            return redirect_empresa(request, 'rh:lista_cargos')
    else:
        form = CargoForm(empresa_ativa=empresa_ativa)

    return render(
        request,
        'rh/cargos/form.html',
        {
            'form': form,
            'titulo': 'Novo Cargo',
        }
    )


# ==========================================================
# EDITAR CARGO
# ==========================================================
def editar_cargo(request, pk):
    """
    Edita um cargo existente da empresa ativa.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de editar um cargo.'
    )
    if redirect_response:
        return redirect_response

    cargo = get_object_or_404(
        Cargo,
        pk=pk,
        empresa=empresa_ativa,
    )

    if request.method == 'POST':
        form = CargoForm(
            request.POST,
            instance=cargo,
            empresa_ativa=empresa_ativa,
        )
        if form.is_valid():
            form.save()

            messages.success(request, 'Cargo atualizado com sucesso.')
            return redirect_empresa(request, 'rh:lista_cargos')
    else:
        form = CargoForm(
            instance=cargo,
            empresa_ativa=empresa_ativa,
        )

    return render(
        request,
        'rh/cargos/form.html',
        {
            'form': form,
            'cargo': cargo,
            'titulo': 'Editar Cargo',
        }
    )


# ==========================================================
# EXCLUIR CARGO
# ==========================================================
def excluir_cargo(request, pk):
    """
    Exclui um cargo da empresa ativa.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de excluir um cargo.'
    )
    if redirect_response:
        return redirect_response

    cargo = get_object_or_404(
        Cargo,
        pk=pk,
        empresa=empresa_ativa,
    )

    if request.method == 'POST':
        cargo.delete()
        messages.success(request, 'Cargo excluído com sucesso.')
        return redirect_empresa(request, 'rh:lista_cargos')

    return render(
        request,
        'rh/cargos/excluir.html',
        {
            'cargo': cargo,
        }
    )