from django.shortcuts import get_object_or_404, render

from auditoria.registry import audit_rh

from ..forms import AfastamentoFuncionarioForm
from ..models import AfastamentoFuncionario, Funcionario
from .base import _empresa_ativa_or_redirect
from .htmx_funcionario import hx_trigger_secao_modal


# ==========================================================
# RENDER DA LISTA
# ==========================================================
def _render_afastamentos_list(request, funcionario):
    """
    Renderiza a partial HTML da lista de afastamentos do funcionário.

    Essa função é reutilizada após:
    - adicionar
    - editar
    - excluir

    Assim mantemos um único ponto de renderização da seção.
    """
    return render(
        request,
        "rh/funcionarios/includes/partials/afastamentos_lista.html",
        {
            "funcionario": funcionario,
            "afastamentos_list": funcionario.afastamentos.all(),
        },
    )


# ==========================================================
# LISTA HTMX
# ==========================================================
def afastamentos_lista(request, pk):
    """
    Retorna a lista de afastamentos do funcionário.

    Normalmente usada para carregar ou recarregar a seção via HTMX.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar.",
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(
        Funcionario.objects.prefetch_related("afastamentos"),
        pk=pk,
        empresa=empresa_ativa,
    )

    return _render_afastamentos_list(request, funcionario)


# ==========================================================
# ADICIONAR
# ==========================================================
def modal_adicionar_afastamento(request, pk):
    """
    Abre e processa o modal de criação de afastamento.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar.",
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)

    if request.method == "POST":
        form = AfastamentoFuncionarioForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.funcionario = funcionario
            item.save()

            audit_rh(
                request,
                'create',
                f'Afastamento registrado — {funcionario.nome}.',
                {'funcionario_id': funcionario.pk, 'afastamento_id': item.pk},
            )
            funcionario.refresh_from_db()

            response = _render_afastamentos_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = hx_trigger_secao_modal(
                "afastamentos",
                "Afastamento registado.",
            )
            return response
    else:
        form = AfastamentoFuncionarioForm()

    return render(
        request,
        "rh/funcionarios/modals/modal_afastamento_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Adicionar afastamento",
            "modo": "criar",
            "item": None,
        },
    )


# ==========================================================
# EDITAR
# ==========================================================
def modal_editar_afastamento(request, pk, afastamento_id):
    """
    Abre e processa o modal de edição de afastamento.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar.",
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(
        AfastamentoFuncionario,
        pk=afastamento_id,
        funcionario=funcionario,
    )

    if request.method == "POST":
        form = AfastamentoFuncionarioForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            audit_rh(
                request,
                'update',
                f'Afastamento atualizado — {funcionario.nome}.',
                {'funcionario_id': funcionario.pk, 'afastamento_id': item.pk},
            )
            funcionario.refresh_from_db()

            response = _render_afastamentos_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = hx_trigger_secao_modal(
                "afastamentos",
                "Afastamento atualizado.",
            )
            return response
    else:
        form = AfastamentoFuncionarioForm(instance=item)

    return render(
        request,
        "rh/funcionarios/modals/modal_afastamento_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Editar afastamento",
            "modo": "editar",
            "item": item,
        },
    )


# ==========================================================
# EXCLUIR
# ==========================================================
def modal_excluir_afastamento(request, pk, afastamento_id):
    """
    Abre e processa o modal de confirmação de exclusão de afastamento.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar.",
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(
        AfastamentoFuncionario,
        pk=afastamento_id,
        funcionario=funcionario,
    )

    if request.method == "POST":
        aid = item.pk
        item.delete()
        audit_rh(
            request,
            'delete',
            f'Afastamento excluído — {funcionario.nome}.',
            {'funcionario_id': funcionario.pk, 'afastamento_id': aid},
        )
        funcionario.refresh_from_db()

        response = _render_afastamentos_list(request, funcionario)
        response["HX-Trigger-After-Settle"] = hx_trigger_secao_modal(
            "afastamentos",
            "Afastamento removido.",
        )
        return response

    return render(
        request,
        "rh/funcionarios/modals/modal_afastamento_confirm_delete.html",
        {
            "funcionario": funcionario,
            "item": item,
        },
    )