"""
Views da seção de férias do funcionário.

Responsabilidades deste arquivo:
- renderizar a lista parcial de férias
- adicionar férias por modal
- editar férias por modal
- excluir férias por modal

Essas views são usadas pela seção HTMX dentro dos detalhes do funcionário.
"""

import json

from django.shortcuts import get_object_or_404, render

from auditoria.registry import audit_rh

from ..forms import FeriasFuncionarioForm
from ..models import FeriasFuncionario, Funcionario
from .base import _empresa_ativa_or_redirect


# ==========================================================
# RENDER DA LISTA
# ==========================================================
def _render_ferias_list(request, funcionario):
    """
    Renderiza a partial HTML da lista de férias do funcionário.

    Essa função é reutilizada após:
    - adicionar
    - editar
    - excluir

    Assim mantemos um único ponto de renderização da seção.
    """
    return render(
        request,
        "rh/funcionarios/includes/partials/ferias_lista.html",
        {
            "funcionario": funcionario,
            "ferias_list": funcionario.ferias.all(),
        },
    )


# ==========================================================
# LISTA HTMX
# ==========================================================
def ferias_lista(request, pk):
    """
    Retorna a lista de férias do funcionário.

    Normalmente usada para carregar ou recarregar a seção via HTMX.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar.",
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(
        Funcionario.objects.prefetch_related("ferias"),
        pk=pk,
        empresa=empresa_ativa,
    )

    return _render_ferias_list(request, funcionario)


# ==========================================================
# ADICIONAR
# ==========================================================
def modal_adicionar_ferias(request, pk):
    """
    Abre e processa o modal de criação de férias.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar.",
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)

    if request.method == "POST":
        form = FeriasFuncionarioForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.funcionario = funcionario
            item.save()

            audit_rh(
                request,
                'create',
                f'Férias registradas — {funcionario.nome}.',
                {'funcionario_id': funcionario.pk, 'ferias_id': item.pk},
            )
            funcionario.refresh_from_db()

            response = _render_ferias_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "ferias"},
            })
            return response
    else:
        form = FeriasFuncionarioForm()

    return render(
        request,
        "rh/funcionarios/modals/modal_ferias_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Adicionar férias",
            "modo": "criar",
            "item": None,
        },
    )


# ==========================================================
# EDITAR
# ==========================================================
def modal_editar_ferias(request, pk, ferias_id):
    """
    Abre e processa o modal de edição de férias.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar.",
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(
        FeriasFuncionario,
        pk=ferias_id,
        funcionario=funcionario,
    )

    if request.method == "POST":
        form = FeriasFuncionarioForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            audit_rh(
                request,
                'update',
                f'Férias atualizadas — {funcionario.nome}.',
                {'funcionario_id': funcionario.pk, 'ferias_id': item.pk},
            )
            funcionario.refresh_from_db()

            response = _render_ferias_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "ferias"},
            })
            return response
    else:
        form = FeriasFuncionarioForm(instance=item)

    return render(
        request,
        "rh/funcionarios/modals/modal_ferias_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Editar férias",
            "modo": "editar",
            "item": item,
        },
    )


# ==========================================================
# EXCLUIR
# ==========================================================
def modal_excluir_ferias(request, pk, ferias_id):
    """
    Abre e processa o modal de confirmação de exclusão de férias.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar.",
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(
        FeriasFuncionario,
        pk=ferias_id,
        funcionario=funcionario,
    )

    if request.method == "POST":
        fid = item.pk
        item.delete()
        audit_rh(
            request,
            'delete',
            f'Férias excluídas — {funcionario.nome}.',
            {'funcionario_id': funcionario.pk, 'ferias_id': fid},
        )
        funcionario.refresh_from_db()

        response = _render_ferias_list(request, funcionario)
        response["HX-Trigger-After-Settle"] = json.dumps({
            "closeSectionModal": True,
            "openSection": {"section": "ferias"},
        })
        return response

    return render(
        request,
        "rh/funcionarios/modals/modal_ferias_confirm_delete.html",
        {
            "funcionario": funcionario,
            "item": item,
        },
    )