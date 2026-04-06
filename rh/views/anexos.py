import json

from django.shortcuts import get_object_or_404, render

from auditoria.registry import audit_rh

from ..forms import AnexoAvulsoFuncionarioForm
from ..models import AnexoAvulsoFuncionario
from .base import _get_funcionario_empresa


# ==========================================================
# COLETA DE ANEXOS GERADOS PELO SISTEMA
# ==========================================================
def _coletar_anexos_sistema(funcionario):
    """
    Junta em uma única lista todos os anexos vindos de outras seções do cadastro.

    Estrutura de cada item:
    - titulo
    - origem
    - data
    - arquivo_url
    - arquivo_nome
    - section
    - health_tab

    section:
        usada para reabrir a seção correta ao clicar no item

    health_tab:
        usada quando o anexo pertence à aba Saúde
    """
    anexos = []

    # --------------------------
    # ASO
    # --------------------------
    for item in funcionario.asos.all():
        if item.anexo:
            anexos.append({
                "titulo": f"ASO {item.get_tipo_display()}",
                "origem": "ASO",
                "data": item.data,
                "arquivo_url": item.anexo.url,
                "arquivo_nome": item.anexo.name.split("/")[-1],
                "section": "saude",
                "health_tab": "aso",
            })

    # --------------------------
    # Certificados
    # --------------------------
    for item in funcionario.certificados.all():
        if item.anexo:
            anexos.append({
                "titulo": f"Certificado {item.tipo}",
                "origem": "Certificados",
                "data": item.data,
                "arquivo_url": item.anexo.url,
                "arquivo_nome": item.anexo.name.split("/")[-1],
                "section": "saude",
                "health_tab": "certificados",
            })

    # --------------------------
    # PCMSO
    # --------------------------
    for item in funcionario.pcmso_registros.all():
        if item.anexo:
            anexos.append({
                "titulo": "PCMSO",
                "origem": "PCMSO",
                "data": item.data_vencimento,
                "arquivo_url": item.anexo.url,
                "arquivo_nome": item.anexo.name.split("/")[-1],
                "section": "saude",
                "health_tab": "pcmso",
            })

    # --------------------------
    # Atestados / Licenças
    # --------------------------
    for item in funcionario.atestados_licencas.all():
        if item.anexo:
            anexos.append({
                "titulo": item.get_tipo_display(),
                "origem": "Atestados / Licenças",
                "data": item.data,
                "arquivo_url": item.anexo.url,
                "arquivo_nome": item.anexo.name.split("/")[-1],
                "section": "saude",
                "health_tab": "atestados",
            })

    # --------------------------
    # Ocorrências de saúde
    # --------------------------
    for item in funcionario.ocorrencias_saude.all():
        if item.anexo:
            anexos.append({
                "titulo": f"Ocorrência {item.get_tipo_display()}",
                "origem": "Ocorrências",
                "data": item.data,
                "arquivo_url": item.anexo.url,
                "arquivo_nome": item.anexo.name.split("/")[-1],
                "section": "saude",
                "health_tab": "ocorrencias",
            })

    # --------------------------
    # Campos diretos de demissão
    # --------------------------
    if getattr(funcionario, "anexo_aviso", None):
        anexos.append({
            "titulo": "Anexo do aviso",
            "origem": "Demissão",
            "data": getattr(funcionario, "data_demissao", None),
            "arquivo_url": funcionario.anexo_aviso.url,
            "arquivo_nome": funcionario.anexo_aviso.name.split("/")[-1],
            "section": "demissao",
            "health_tab": None,
        })

    if getattr(funcionario, "rescisao_assinada", None):
        anexos.append({
            "titulo": "Rescisão assinada",
            "origem": "Demissão",
            "data": getattr(funcionario, "data_demissao", None),
            "arquivo_url": funcionario.rescisao_assinada.url,
            "arquivo_nome": funcionario.rescisao_assinada.name.split("/")[-1],
            "section": "demissao",
            "health_tab": None,
        })

    # Ordena do mais recente para o mais antigo
    anexos.sort(key=lambda x: (x["data"] is not None, x["data"]), reverse=True)

    return anexos


# ==========================================================
# RENDER DA LISTA DE ANEXOS AVULSOS
# ==========================================================
def _render_anexos_avulsos_list(request, funcionario):
    """
    Renderiza a partial com a lista de anexos avulsos.

    Essa função é reutilizada após:
    - adicionar
    - editar
    - excluir
    """
    return render(
        request,
        "rh/funcionarios/includes/partials/anexos_avulsos_lista.html",
        {
            "funcionario": funcionario,
            "anexos_avulsos_list": funcionario.anexos_avulsos.all(),
        },
    )


# ==========================================================
# CONTEXTO DA SEÇÃO DE ANEXOS
# ==========================================================
def secao_anexos_context(funcionario):
    """
    Retorna o contexto necessário para montar a seção de anexos
    dentro da tela de detalhes do funcionário.
    """
    return {
        "anexos_sistema_list": _coletar_anexos_sistema(funcionario),
        "anexos_avulsos_list": funcionario.anexos_avulsos.all(),
    }


# ==========================================================
# LISTA HTMX
# ==========================================================
def anexos_avulsos_lista(request, pk):
    """
    Retorna a lista de anexos avulsos do funcionário.

    Normalmente usada para carregar ou atualizar a seção via HTMX.
    """
    funcionario, redirect_response = _get_funcionario_empresa(request, pk)
    if redirect_response:
        return redirect_response

    return _render_anexos_avulsos_list(request, funcionario)


# ==========================================================
# ADICIONAR ANEXO AVULSO
# ==========================================================
def modal_adicionar_anexo_avulso(request, pk):
    """
    Abre e processa o modal de criação de anexo avulso.
    """
    funcionario, redirect_response = _get_funcionario_empresa(request, pk)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = AnexoAvulsoFuncionarioForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.funcionario = funcionario
            item.save()

            audit_rh(
                request,
                'create',
                f'Anexo avulso adicionado — {funcionario.nome}.',
                {'funcionario_id': funcionario.pk, 'anexo_avulso_id': item.pk},
            )
            funcionario.refresh_from_db()

            response = _render_anexos_avulsos_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "anexos"},
            })
            return response
    else:
        form = AnexoAvulsoFuncionarioForm()

    return render(
        request,
        "rh/funcionarios/modals/modal_anexo_avulso_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Adicionar anexo",
            "modo": "criar",
            "item": None,
        },
    )


# ==========================================================
# EDITAR ANEXO AVULSO
# ==========================================================
def modal_editar_anexo_avulso(request, pk, anexo_id):
    """
    Abre e processa o modal de edição de anexo avulso.
    """
    funcionario, redirect_response = _get_funcionario_empresa(request, pk)
    if redirect_response:
        return redirect_response

    item = get_object_or_404(
        AnexoAvulsoFuncionario,
        pk=anexo_id,
        funcionario=funcionario,
    )

    if request.method == "POST":
        form = AnexoAvulsoFuncionarioForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            audit_rh(
                request,
                'update',
                f'Anexo avulso atualizado — {funcionario.nome}.',
                {'funcionario_id': funcionario.pk, 'anexo_avulso_id': item.pk},
            )
            funcionario.refresh_from_db()

            response = _render_anexos_avulsos_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "anexos"},
            })
            return response
    else:
        form = AnexoAvulsoFuncionarioForm(instance=item)

    return render(
        request,
        "rh/funcionarios/modals/modal_anexo_avulso_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Editar anexo",
            "modo": "editar",
            "item": item,
        },
    )


# ==========================================================
# EXCLUIR ANEXO AVULSO
# ==========================================================
def modal_excluir_anexo_avulso(request, pk, anexo_id):
    """
    Abre e processa o modal de confirmação de exclusão de anexo avulso.
    """
    funcionario, redirect_response = _get_funcionario_empresa(request, pk)
    if redirect_response:
        return redirect_response

    item = get_object_or_404(
        AnexoAvulsoFuncionario,
        pk=anexo_id,
        funcionario=funcionario,
    )

    if request.method == "POST":
        aid = item.pk
        item.delete()
        audit_rh(
            request,
            'delete',
            f'Anexo avulso excluído — {funcionario.nome}.',
            {'funcionario_id': funcionario.pk, 'anexo_avulso_id': aid},
        )
        funcionario.refresh_from_db()

        response = _render_anexos_avulsos_list(request, funcionario)
        response["HX-Trigger-After-Settle"] = json.dumps({
            "closeSectionModal": True,
            "openSection": {"section": "anexos"},
        })
        return response

    return render(
        request,
        "rh/funcionarios/modals/modal_anexo_avulso_confirm_delete.html",
        {
            "funcionario": funcionario,
            "item": item,
        },
    )