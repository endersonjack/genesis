"""
Views da seção de saúde do funcionário.

Responsabilidades deste arquivo:
- renderizar listas parciais da aba Saúde
- adicionar, editar e excluir itens de saúde via modal
- manter a aba correta aberta após operações HTMX

Subseções atendidas:
- ASO
- Certificados
- PCMSO
- Atestados / Licenças
- Ocorrências de Saúde
"""

import json

from django.shortcuts import get_object_or_404, render

from ..forms import (
    ASOFuncionarioForm,
    AtestadoLicencaFuncionarioForm,
    CertificadoFuncionarioForm,
    OcorrenciaSaudeFuncionarioForm,
    PCMSOFuncionarioForm,
)
from ..models import (
    ASOFuncionario,
    AtestadoLicencaFuncionario,
    CertificadoFuncionario,
    Funcionario,
    OcorrenciaSaudeFuncionario,
    PCMSOFuncionario,
)
from .base import _empresa_ativa_or_redirect


# ==========================================================
# HELPERS
# ==========================================================
def _get_funcionario_saude(request, pk):
    """
    Busca o funcionário da empresa ativa com os relacionamentos
    usados na aba de saúde já pré-carregados.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar.",
    )
    if redirect_response:
        return None, redirect_response

    funcionario = get_object_or_404(
        Funcionario.objects.prefetch_related(
            "asos",
            "certificados",
            "pcmso_registros",
            "atestados_licencas",
            "ocorrencias_saude",
        ),
        pk=pk,
        empresa=empresa_ativa,
    )
    return funcionario, None


def _build_saude_trigger(health_tab):
    """
    Monta o trigger HTMX padrão para:
    - fechar o modal
    - reabrir a seção saúde
    - manter a aba correta ativa
    """
    return json.dumps({
        "closeSectionModal": True,
        "openSection": {
            "section": "saude",
            "healthTab": health_tab,
        },
    })


# ==========================================================
# ASO
# ==========================================================
def _render_aso_list(request, funcionario):
    """
    Renderiza a partial da lista de ASOs do funcionário.
    """
    return render(
        request,
        "rh/funcionarios/includes/partials/aso_lista.html",
        {
            "funcionario": funcionario,
            "aso_list": funcionario.asos.all(),
        },
    )


def aso_lista(request, pk):
    """
    Retorna a lista HTMX de ASOs.
    """
    funcionario, redirect_response = _get_funcionario_saude(request, pk)
    if redirect_response:
        return redirect_response

    return _render_aso_list(request, funcionario)


def modal_adicionar_aso(request, pk):
    """
    Modal para adicionar ASO.
    """
    funcionario, redirect_response = _get_funcionario_saude(request, pk)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = ASOFuncionarioForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.funcionario = funcionario
            item.save()

            funcionario.refresh_from_db()

            response = _render_aso_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = _build_saude_trigger("aso")
            return response
    else:
        form = ASOFuncionarioForm()

    return render(
        request,
        "rh/funcionarios/modals/modal_aso_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Adicionar ASO",
            "modo": "criar",
            "item": None,
        },
    )


def modal_editar_aso(request, pk, aso_id):
    """
    Modal para editar ASO.
    """
    funcionario, redirect_response = _get_funcionario_saude(request, pk)
    if redirect_response:
        return redirect_response

    item = get_object_or_404(
        ASOFuncionario,
        pk=aso_id,
        funcionario=funcionario,
    )

    if request.method == "POST":
        form = ASOFuncionarioForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()

            funcionario.refresh_from_db()

            response = _render_aso_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = _build_saude_trigger("aso")
            return response
    else:
        form = ASOFuncionarioForm(instance=item)

    return render(
        request,
        "rh/funcionarios/modals/modal_aso_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Editar ASO",
            "modo": "editar",
            "item": item,
        },
    )


def modal_excluir_aso(request, pk, aso_id):
    """
    Modal para excluir ASO.
    """
    funcionario, redirect_response = _get_funcionario_saude(request, pk)
    if redirect_response:
        return redirect_response

    item = get_object_or_404(
        ASOFuncionario,
        pk=aso_id,
        funcionario=funcionario,
    )

    if request.method == "POST":
        item.delete()

        funcionario.refresh_from_db()

        response = _render_aso_list(request, funcionario)
        response["HX-Trigger-After-Settle"] = _build_saude_trigger("aso")
        return response

    return render(
        request,
        "rh/funcionarios/modals/modal_aso_confirm_delete.html",
        {
            "funcionario": funcionario,
            "item": item,
        },
    )


# ==========================================================
# CERTIFICADOS
# ==========================================================
def _render_certificados_list(request, funcionario):
    """
    Renderiza a partial da lista de certificados do funcionário.
    """
    return render(
        request,
        "rh/funcionarios/includes/partials/certificados_lista.html",
        {
            "funcionario": funcionario,
            "certificados_list": funcionario.certificados.all(),
        },
    )


def certificados_lista(request, pk):
    """
    Retorna a lista HTMX de certificados.
    """
    funcionario, redirect_response = _get_funcionario_saude(request, pk)
    if redirect_response:
        return redirect_response

    return _render_certificados_list(request, funcionario)


def modal_adicionar_certificado(request, pk):
    """
    Modal para adicionar certificado.
    """
    funcionario, redirect_response = _get_funcionario_saude(request, pk)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = CertificadoFuncionarioForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.funcionario = funcionario
            item.save()

            funcionario.refresh_from_db()

            response = _render_certificados_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = _build_saude_trigger("certificados")
            return response
    else:
        form = CertificadoFuncionarioForm()

    return render(
        request,
        "rh/funcionarios/modals/modal_certificado_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Adicionar certificado",
            "modo": "criar",
            "item": None,
        },
    )


def modal_editar_certificado(request, pk, certificado_id):
    """
    Modal para editar certificado.
    """
    funcionario, redirect_response = _get_funcionario_saude(request, pk)
    if redirect_response:
        return redirect_response

    item = get_object_or_404(
        CertificadoFuncionario,
        pk=certificado_id,
        funcionario=funcionario,
    )

    if request.method == "POST":
        form = CertificadoFuncionarioForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()

            funcionario.refresh_from_db()

            response = _render_certificados_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = _build_saude_trigger("certificados")
            return response
    else:
        form = CertificadoFuncionarioForm(instance=item)

    return render(
        request,
        "rh/funcionarios/modals/modal_certificado_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Editar certificado",
            "modo": "editar",
            "item": item,
        },
    )


def modal_excluir_certificado(request, pk, certificado_id):
    """
    Modal para excluir certificado.
    """
    funcionario, redirect_response = _get_funcionario_saude(request, pk)
    if redirect_response:
        return redirect_response

    item = get_object_or_404(
        CertificadoFuncionario,
        pk=certificado_id,
        funcionario=funcionario,
    )

    if request.method == "POST":
        item.delete()

        funcionario.refresh_from_db()

        response = _render_certificados_list(request, funcionario)
        response["HX-Trigger-After-Settle"] = _build_saude_trigger("certificados")
        return response

    return render(
        request,
        "rh/funcionarios/modals/modal_certificado_confirm_delete.html",
        {
            "funcionario": funcionario,
            "item": item,
        },
    )


# ==========================================================
# PCMSO
# ==========================================================
def _render_pcmso_list(request, funcionario):
    """
    Renderiza a partial da lista de PCMSO do funcionário.
    """
    return render(
        request,
        "rh/funcionarios/includes/partials/pcmso_lista.html",
        {
            "funcionario": funcionario,
            "pcmso_list": funcionario.pcmso_registros.all(),
        },
    )


def pcmso_lista(request, pk):
    """
    Retorna a lista HTMX de PCMSO.
    """
    funcionario, redirect_response = _get_funcionario_saude(request, pk)
    if redirect_response:
        return redirect_response

    return _render_pcmso_list(request, funcionario)


def modal_adicionar_pcmso(request, pk):
    """
    Modal para adicionar PCMSO.
    """
    funcionario, redirect_response = _get_funcionario_saude(request, pk)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = PCMSOFuncionarioForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.funcionario = funcionario
            item.save()

            funcionario.refresh_from_db()

            response = _render_pcmso_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = _build_saude_trigger("pcmso")
            return response
    else:
        form = PCMSOFuncionarioForm()

    return render(
        request,
        "rh/funcionarios/modals/modal_pcmso_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Adicionar PCMSO",
            "modo": "criar",
            "item": None,
        },
    )


def modal_editar_pcmso(request, pk, pcmso_id):
    """
    Modal para editar PCMSO.
    """
    funcionario, redirect_response = _get_funcionario_saude(request, pk)
    if redirect_response:
        return redirect_response

    item = get_object_or_404(
        PCMSOFuncionario,
        pk=pcmso_id,
        funcionario=funcionario,
    )

    if request.method == "POST":
        form = PCMSOFuncionarioForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()

            funcionario.refresh_from_db()

            response = _render_pcmso_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = _build_saude_trigger("pcmso")
            return response
    else:
        form = PCMSOFuncionarioForm(instance=item)

    return render(
        request,
        "rh/funcionarios/modals/modal_pcmso_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Editar PCMSO",
            "modo": "editar",
            "item": item,
        },
    )


def modal_excluir_pcmso(request, pk, pcmso_id):
    """
    Modal para excluir PCMSO.
    """
    funcionario, redirect_response = _get_funcionario_saude(request, pk)
    if redirect_response:
        return redirect_response

    item = get_object_or_404(
        PCMSOFuncionario,
        pk=pcmso_id,
        funcionario=funcionario,
    )

    if request.method == "POST":
        item.delete()

        funcionario.refresh_from_db()

        response = _render_pcmso_list(request, funcionario)
        response["HX-Trigger-After-Settle"] = _build_saude_trigger("pcmso")
        return response

    return render(
        request,
        "rh/funcionarios/modals/modal_pcmso_confirm_delete.html",
        {
            "funcionario": funcionario,
            "item": item,
        },
    )


# ==========================================================
# ATESTADOS / LICENÇAS
# ==========================================================
def _render_atestados_licencas_list(request, funcionario):
    """
    Renderiza a partial da lista de atestados/licenças.
    """
    return render(
        request,
        "rh/funcionarios/includes/partials/atestados_licencas_lista.html",
        {
            "funcionario": funcionario,
            "atestados_licencas_list": funcionario.atestados_licencas.all(),
        },
    )


def atestados_licencas_lista(request, pk):
    """
    Retorna a lista HTMX de atestados/licenças.
    """
    funcionario, redirect_response = _get_funcionario_saude(request, pk)
    if redirect_response:
        return redirect_response

    return _render_atestados_licencas_list(request, funcionario)


def modal_adicionar_atestado_licenca(request, pk):
    """
    Modal para adicionar atestado/licença.
    """
    funcionario, redirect_response = _get_funcionario_saude(request, pk)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = AtestadoLicencaFuncionarioForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.funcionario = funcionario
            item.save()

            funcionario.refresh_from_db()

            response = _render_atestados_licencas_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = _build_saude_trigger("atestados")
            return response
    else:
        form = AtestadoLicencaFuncionarioForm()

    return render(
        request,
        "rh/funcionarios/modals/modal_atestado_licenca_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Adicionar atestado / licença",
            "modo": "criar",
            "item": None,
        },
    )


def modal_editar_atestado_licenca(request, pk, atestado_id):
    """
    Modal para editar atestado/licença.
    """
    funcionario, redirect_response = _get_funcionario_saude(request, pk)
    if redirect_response:
        return redirect_response

    item = get_object_or_404(
        AtestadoLicencaFuncionario,
        pk=atestado_id,
        funcionario=funcionario,
    )

    if request.method == "POST":
        form = AtestadoLicencaFuncionarioForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()

            funcionario.refresh_from_db()

            response = _render_atestados_licencas_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = _build_saude_trigger("atestados")
            return response
    else:
        form = AtestadoLicencaFuncionarioForm(instance=item)

    return render(
        request,
        "rh/funcionarios/modals/modal_atestado_licenca_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Editar atestado / licença",
            "modo": "editar",
            "item": item,
        },
    )


def modal_excluir_atestado_licenca(request, pk, atestado_id):
    """
    Modal para excluir atestado/licença.
    """
    funcionario, redirect_response = _get_funcionario_saude(request, pk)
    if redirect_response:
        return redirect_response

    item = get_object_or_404(
        AtestadoLicencaFuncionario,
        pk=atestado_id,
        funcionario=funcionario,
    )

    if request.method == "POST":
        item.delete()

        funcionario.refresh_from_db()

        response = _render_atestados_licencas_list(request, funcionario)
        response["HX-Trigger-After-Settle"] = _build_saude_trigger("atestados")
        return response

    return render(
        request,
        "rh/funcionarios/modals/modal_atestado_licenca_confirm_delete.html",
        {
            "funcionario": funcionario,
            "item": item,
        },
    )


# ==========================================================
# OCORRÊNCIAS DE SAÚDE
# ==========================================================
def _render_ocorrencias_saude_list(request, funcionario):
    """
    Renderiza a partial da lista de ocorrências de saúde.
    """
    return render(
        request,
        "rh/funcionarios/includes/partials/ocorrencias_saude_lista.html",
        {
            "funcionario": funcionario,
            "ocorrencias_saude_list": funcionario.ocorrencias_saude.all(),
        },
    )


def ocorrencias_saude_lista(request, pk):
    """
    Retorna a lista HTMX de ocorrências de saúde.
    """
    funcionario, redirect_response = _get_funcionario_saude(request, pk)
    if redirect_response:
        return redirect_response

    return _render_ocorrencias_saude_list(request, funcionario)


def modal_adicionar_ocorrencia_saude(request, pk):
    """
    Modal para adicionar ocorrência de saúde.
    """
    funcionario, redirect_response = _get_funcionario_saude(request, pk)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = OcorrenciaSaudeFuncionarioForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.funcionario = funcionario
            item.save()

            funcionario.refresh_from_db()

            response = _render_ocorrencias_saude_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = _build_saude_trigger("ocorrencias")
            return response
    else:
        form = OcorrenciaSaudeFuncionarioForm()

    return render(
        request,
        "rh/funcionarios/modals/modal_ocorrencia_saude_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Adicionar ocorrência",
            "modo": "criar",
            "item": None,
        },
    )


def modal_editar_ocorrencia_saude(request, pk, ocorrencia_id):
    """
    Modal para editar ocorrência de saúde.
    """
    funcionario, redirect_response = _get_funcionario_saude(request, pk)
    if redirect_response:
        return redirect_response

    item = get_object_or_404(
        OcorrenciaSaudeFuncionario,
        pk=ocorrencia_id,
        funcionario=funcionario,
    )

    if request.method == "POST":
        form = OcorrenciaSaudeFuncionarioForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()

            funcionario.refresh_from_db()

            response = _render_ocorrencias_saude_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = _build_saude_trigger("ocorrencias")
            return response
    else:
        form = OcorrenciaSaudeFuncionarioForm(instance=item)

    return render(
        request,
        "rh/funcionarios/modals/modal_ocorrencia_saude_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Editar ocorrência",
            "modo": "editar",
            "item": item,
        },
    )


def modal_excluir_ocorrencia_saude(request, pk, ocorrencia_id):
    """
    Modal para excluir ocorrência de saúde.
    """
    funcionario, redirect_response = _get_funcionario_saude(request, pk)
    if redirect_response:
        return redirect_response

    item = get_object_or_404(
        OcorrenciaSaudeFuncionario,
        pk=ocorrencia_id,
        funcionario=funcionario,
    )

    if request.method == "POST":
        item.delete()

        funcionario.refresh_from_db()

        response = _render_ocorrencias_saude_list(request, funcionario)
        response["HX-Trigger-After-Settle"] = _build_saude_trigger("ocorrencias")
        return response

    return render(
        request,
        "rh/funcionarios/modals/modal_ocorrencia_saude_confirm_delete.html",
        {
            "funcionario": funcionario,
            "item": item,
        },
    )