"""
Views da seção de dependentes do funcionário.

Responsabilidades deste arquivo:
- renderizar a lista parcial de dependentes
- adicionar dependente por modal
- editar dependente por modal
- excluir dependente por modal

Essas views são usadas pela seção HTMX dentro dos detalhes do funcionário.
"""

import json

from django.shortcuts import get_object_or_404, render

from ..forms import DependenteForm
from ..models import Dependente, Funcionario
from .base import _empresa_ativa_or_redirect


# ==========================================================
# RENDER DA LISTA
# ==========================================================
def _render_dependentes_list(request, funcionario):
    """
    Renderiza a partial HTML da lista de dependentes do funcionário.

    Essa função é reutilizada após:
    - adicionar
    - editar
    - excluir

    Assim mantemos um único ponto de renderização da seção.
    """
    return render(
        request,
        "rh/funcionarios/includes/partials/dependentes_lista.html",
        {
            "funcionario": funcionario,
            "dependentes_list": funcionario.dependentes.all(),
        },
    )


# ==========================================================
# LISTA HTMX
# ==========================================================
def dependentes_lista(request, pk):
    """
    Retorna a lista de dependentes do funcionário.

    Normalmente usada para carregar ou recarregar a seção via HTMX.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar.",
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(
        Funcionario.objects.prefetch_related("dependentes"),
        pk=pk,
        empresa=empresa_ativa,
    )

    return _render_dependentes_list(request, funcionario)


# ==========================================================
# ADICIONAR
# ==========================================================
def modal_adicionar_dependente(request, pk):
    """
    Abre e processa o modal de criação de dependente.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar.",
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)

    if request.method == "POST":
        form = DependenteForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.funcionario = funcionario
            item.save()

            funcionario.refresh_from_db()

            response = _render_dependentes_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "dependentes"},
            })
            return response
    else:
        form = DependenteForm()

    return render(
        request,
        "rh/funcionarios/modals/modal_dependente_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Adicionar dependente",
            "modo": "criar",
            "item": None,
        },
    )


# ==========================================================
# EDITAR
# ==========================================================
def modal_editar_dependente(request, pk, dependente_id):
    """
    Abre e processa o modal de edição de dependente.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar.",
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(
        Dependente,
        pk=dependente_id,
        funcionario=funcionario,
    )

    if request.method == "POST":
        form = DependenteForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()

            funcionario.refresh_from_db()

            response = _render_dependentes_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "dependentes"},
            })
            return response
    else:
        form = DependenteForm(instance=item)

    return render(
        request,
        "rh/funcionarios/modals/modal_dependente_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Editar dependente",
            "modo": "editar",
            "item": item,
        },
    )


# ==========================================================
# EXCLUIR
# ==========================================================
def modal_excluir_dependente(request, pk, dependente_id):
    """
    Abre e processa o modal de confirmação de exclusão de dependente.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar.",
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(
        Dependente,
        pk=dependente_id,
        funcionario=funcionario,
    )

    if request.method == "POST":
        item.delete()

        funcionario.refresh_from_db()

        response = _render_dependentes_list(request, funcionario)
        response["HX-Trigger-After-Settle"] = json.dumps({
            "closeSectionModal": True,
            "openSection": {"section": "dependentes"},
        })
        return response

    return render(
        request,
        "rh/funcionarios/modals/modal_dependente_confirm_delete.html",
        {
            "funcionario": funcionario,
            "item": item,
        },
    )