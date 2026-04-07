"""
Views de modais principais do funcionário.

Responsabilidades deste arquivo:
- cadastro rápido de funcionário
- edição por modal das seções principais:
    - pessoais
    - admissão
    - demissão
    - bancários
    - outros

Observação:
- férias, afastamentos, dependentes, saúde e anexos ficam em arquivos próprios
- este arquivo concentra somente os modais principais do cadastro
"""

from datetime import datetime

from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render

from auditoria.registry import audit_rh
from core.urlutils import reverse_empresa

from ..forms import (
    FuncionarioAdmissaoForm,
    FuncionarioBancariosForm,
    FuncionarioCadastroRapidoForm,
    FuncionarioDadosPessoaisForm,
    FuncionarioDemissaoForm,
    FuncionarioOutrosForm,
)
from .base import _empresa_ativa_or_redirect, _get_funcionario_empresa
from .htmx_funcionario import hx_trigger_secao_modal
from ..utils.historico import registrar_alteracao_situacao


# ==========================================================
# NOVO FUNCIONÁRIO - CADASTRO RÁPIDO
# ==========================================================
@transaction.atomic
def modal_novo_funcionario_rapido(request):
    """
    Modal de criação rápida de funcionário.

    Fluxo:
    - abre um modal simples
    - salva apenas os dados iniciais
    - redireciona via HTMX para os detalhes do funcionário recém-criado
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de cadastrar funcionários.'
    )
    if redirect_response:
        return redirect_response

    if request.method == 'POST':
        form = FuncionarioCadastroRapidoForm(
            request.POST,
            empresa_ativa=empresa_ativa,
        )

        if form.is_valid():
            funcionario = form.save(commit=False)
            funcionario.empresa = empresa_ativa
            funcionario.save()

            audit_rh(
                request,
                'create',
                f'Funcionário "{funcionario.nome}" cadastrado (cadastro rápido).',
                {'funcionario_id': funcionario.pk},
            )
            response = HttpResponse(status=204)
            response['HX-Redirect'] = reverse_empresa(
                request,
                'rh:detalhes_funcionario',
                kwargs={'pk': funcionario.pk},
            )
            return response
    else:
        form = FuncionarioCadastroRapidoForm(empresa_ativa=empresa_ativa)

    return render(
        request,
        'rh/funcionarios/modal_novo_rapido.html',
        {
            'form': form,
        }
    )


# ==========================================================
# MODAL - DADOS PESSOAIS
# ==========================================================
def modal_editar_pessoais(request, pk):
    """
    Modal da seção de dados pessoais.
    """
    funcionario, redirect_response = _get_funcionario_empresa(request, pk)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = FuncionarioDadosPessoaisForm(
            request.POST,
            request.FILES,
            instance=funcionario,
        )
        if form.is_valid():
            form.save()
            funcionario.refresh_from_db()

            audit_rh(
                request,
                'update',
                f'Funcionário "{funcionario.nome}": dados pessoais atualizados (modal).',
                {'funcionario_id': funcionario.pk},
            )
            response = render(
                request,
                "rh/funcionarios/modals/pessoais_success.html",
                {"funcionario": funcionario},
            )
            response["HX-Trigger-After-Settle"] = hx_trigger_secao_modal(
                "pessoais",
                "Dados pessoais atualizados.",
            )
            return response
    else:
        form = FuncionarioDadosPessoaisForm(instance=funcionario)

    return render(
        request,
        "rh/funcionarios/modals/modal_pessoais_form.html",
        {
            "funcionario": funcionario,
            "form": form,
        },
    )


# ==========================================================
# MODAL - ADMISSÃO
# ==========================================================
def modal_editar_admissao(request, pk):
    """
    Modal da seção de admissão.

    Observação:
    registra histórico quando a situação do funcionário for alterada.
    """
    funcionario, redirect_response = _get_funcionario_empresa(request, pk)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        situacao_antiga = funcionario.situacao_atual

        form = FuncionarioAdmissaoForm(
            request.POST,
            request.FILES,
            instance=funcionario,
            empresa_ativa=getattr(request, "empresa_ativa", None),
        )

        if form.is_valid():
            funcionario = form.save()
            situacao_nova = funcionario.situacao_atual

            registrar_alteracao_situacao(
                funcionario=funcionario,
                usuario=request.user,
                situacao_antiga=situacao_antiga,
                situacao_nova=situacao_nova,
            )

            audit_rh(
                request,
                'update',
                f'Funcionário "{funcionario.nome}": admissão atualizada (modal).',
                {'funcionario_id': funcionario.pk},
            )
            response = render(
                request,
                "rh/funcionarios/modals/admissao_success.html",
                {"funcionario": funcionario},
            )
            response["HX-Trigger-After-Settle"] = hx_trigger_secao_modal(
                "admissao",
                "Admissão atualizada.",
            )
            return response
    else:
        form = FuncionarioAdmissaoForm(
            instance=funcionario,
            empresa_ativa=getattr(request, "empresa_ativa", None),
        )

    return render(
        request,
        "rh/funcionarios/modals/modal_admissao_form.html",
        {
            "funcionario": funcionario,
            "form": form,
        },
    )


# ==========================================================
# MODAL - DEMISSÃO
# ==========================================================
def modal_editar_demissao(request, pk):
    """
    Modal da seção de demissão.

    Regras:
    - se houver data_demissao, a situação vai para 'inativo' (desativado)
    - se remover a data e a situação ainda estiver como 'inativo',
      volta para 'admitido'
    - calcula o alerta de exame demissional antes de salvar
    """
    funcionario, redirect_response = _get_funcionario_empresa(request, pk)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = FuncionarioDemissaoForm(
            request.POST,
            request.FILES,
            instance=funcionario,
        )
    else:
        form = FuncionarioDemissaoForm(instance=funcionario)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)

        if obj.data_demissao:
            obj.situacao_atual = 'inativo'
        elif obj.situacao_atual == 'inativo':
            obj.situacao_atual = 'admitido'

        obj.save()
        funcionario.refresh_from_db()

        audit_rh(
            request,
            'update',
            f'Funcionário "{funcionario.nome}": demissão atualizada (modal).',
            {'funcionario_id': funcionario.pk},
        )
        response = render(
            request,
            "rh/funcionarios/modals/demissao_success.html",
            {"funcionario": funcionario},
        )
        response["HX-Trigger-After-Settle"] = hx_trigger_secao_modal(
            "demissao",
            "Demissão atualizada.",
        )
        return response

    # --------------------------------------------------
    # LÓGICA DO EXAME DEMISSIONAL
    # --------------------------------------------------
    data_admissao = funcionario.data_admissao
    data_demissao = funcionario.data_demissao
    exame_info_indisponivel = False
    precisa_exame_demissional = False

    # Em POST, usamos o valor digitado no form,
    # mesmo antes de salvar, para atualizar o alerta do modal.
    if request.method == "POST":
        valor_data_demissao = form.data.get("data_demissao")
        if valor_data_demissao:
            try:
                data_demissao = datetime.strptime(
                    valor_data_demissao,
                    "%Y-%m-%d"
                ).date()
            except ValueError:
                data_demissao = funcionario.data_demissao

    if data_admissao and data_demissao:
        precisa_exame_demissional = (data_demissao - data_admissao).days > 90
    else:
        exame_info_indisponivel = True

    return render(
        request,
        "rh/funcionarios/modals/modal_demissao_form.html",
        {
            "form": form,
            "funcionario": funcionario,
            "precisa_exame_demissional": precisa_exame_demissional,
            "exame_info_indisponivel": exame_info_indisponivel,
        }
    )


# ==========================================================
# MODAL - DADOS BANCÁRIOS
# ==========================================================
def modal_editar_bancarios(request, pk):
    """
    Modal da seção de dados bancários.
    """
    funcionario, redirect_response = _get_funcionario_empresa(request, pk)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = FuncionarioBancariosForm(
            request.POST,
            instance=funcionario,
        )

        if form.is_valid():
            form.save()
            funcionario.refresh_from_db()

            audit_rh(
                request,
                'update',
                f'Funcionário "{funcionario.nome}": dados bancários atualizados (modal).',
                {'funcionario_id': funcionario.pk},
            )
            response = render(
                request,
                "rh/funcionarios/modals/bancarios_success.html",
                {"funcionario": funcionario},
            )

            response["HX-Trigger-After-Settle"] = hx_trigger_secao_modal(
                "bancarios",
                "Dados bancários atualizados.",
            )
            return response
    else:
        form = FuncionarioBancariosForm(instance=funcionario)

    return render(
        request,
        "rh/funcionarios/modals/modal_bancarios_form.html",
        {
            "form": form,
            "funcionario": funcionario,
        }
    )


# ==========================================================
# MODAL - OUTROS DADOS
# ==========================================================
def modal_editar_outros(request, pk):
    """
    Modal da seção de outros dados do funcionário.
    """
    funcionario, redirect_response = _get_funcionario_empresa(request, pk)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = FuncionarioOutrosForm(
            request.POST,
            instance=funcionario,
        )

        if form.is_valid():
            form.save()
            funcionario.refresh_from_db()

            audit_rh(
                request,
                'update',
                f'Funcionário "{funcionario.nome}": outros dados atualizados (modal).',
                {'funcionario_id': funcionario.pk},
            )
            response = render(
                request,
                "rh/funcionarios/modals/outros_success.html",
                {"funcionario": funcionario},
            )

            response["HX-Trigger-After-Settle"] = hx_trigger_secao_modal(
                "outros",
                "Outros dados atualizados.",
            )
            return response
    else:
        form = FuncionarioOutrosForm(instance=funcionario)

    return render(
        request,
        "rh/funcionarios/modals/modal_outros_form.html",
        {
            "form": form,
            "funcionario": funcionario,
        }
    )