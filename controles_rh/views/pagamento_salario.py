from __future__ import annotations

import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from auditoria.registry import audit_controles_rh

from core.urlutils import redirect_empresa, reverse_empresa

from controles_rh.forms import PagamentoSalarioControleForm, PagamentoSalarioLinhaForm
from controles_rh.models import (
    Competencia,
    PagamentoSalarioControle,
    PagamentoSalarioLinha,
)
from controles_rh.views.alteracao_folha import (
    _fmt_af_moeda,
    _fmt_tempo_desde_admissao,
    _month_bounds,
)
from controles_rh.views.vale_transporte import _get_funcionarios_para_vt


def _is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def _get_competencia_empresa(request, competencia_pk):
    empresa_ativa = getattr(request, 'empresa_ativa', None)
    queryset = Competencia.objects.select_related('empresa')
    if empresa_ativa:
        queryset = queryset.filter(empresa=empresa_ativa)
    else:
        queryset = queryset.none()
    return get_object_or_404(queryset, pk=competencia_pk)


def _get_controle_pagamento_empresa(request, controle_pk):
    empresa_ativa = getattr(request, 'empresa_ativa', None)
    queryset = PagamentoSalarioControle.objects.select_related(
        'competencia',
        'competencia__empresa',
    )
    if empresa_ativa:
        queryset = queryset.filter(competencia__empresa=empresa_ativa)
    else:
        queryset = queryset.none()
    return get_object_or_404(queryset, pk=controle_pk)


def _ordenacao_linhas(valor: str | None) -> str:
    if valor in {'cargo', 'lotacao', 'tempo'}:
        return valor
    return 'nome'


def _titulo_padrao_pagamento_salario(competencia: Competencia) -> str:
    total = PagamentoSalarioControle.objects.filter(competencia=competencia).count() + 1
    return 'Pagamento de salário' if total == 1 else f'Pagamento de salário {total}'


def _modo_criacao_pagamento(request):
    if request.method == 'POST':
        return (request.POST.get('criacao_modo') or '').strip()
    return (request.GET.get('modo') or '').strip()


def _origem_pagamento_pk(request):
    if request.method == 'POST':
        return (request.POST.get('origem_controle') or '').strip()
    return (request.GET.get('origem_controle') or '').strip()


def _competencias_anteriores_pagamento_qs(competencia: Competencia):
    return (
        Competencia.objects.filter(empresa_id=competencia.empresa_id)
        .filter(Q(ano__lt=competencia.ano) | Q(ano=competencia.ano, mes__lt=competencia.mes))
        .order_by('-ano', '-mes', '-id')
    )


def _pagamentos_salario_anteriores(competencia: Competencia):
    return (
        PagamentoSalarioControle.objects.filter(
            competencia__in=_competencias_anteriores_pagamento_qs(competencia)
        )
        .select_related('competencia')
        .order_by('-competencia__ano', '-competencia__mes', 'nome', 'id')
    )


def _get_pagamento_origem_clone(request, competencia: Competencia, origem_controle_pk):
    if not str(origem_controle_pk).isdigit():
        return None
    return _pagamentos_salario_anteriores(competencia).filter(pk=int(origem_controle_pk)).first()


def _queryset_linhas(controle: PagamentoSalarioControle, *, ordenacao: str = 'nome'):
    orderings = {
        'nome': ('funcionario__nome', 'id'),
        'cargo': ('funcionario__cargo__nome', 'funcionario__nome', 'id'),
        'lotacao': ('funcionario__lotacao__nome', 'funcionario__nome', 'id'),
        'tempo': (F('funcionario__data_admissao').asc(nulls_last=True), 'funcionario__nome', 'id'),
    }
    return (
        PagamentoSalarioLinha.objects.filter(controle=controle)
        .select_related(
            'funcionario',
            'funcionario__cargo',
            'funcionario__lotacao',
            'funcionario__banco',
            'conta_bancaria_empresa',
        )
        .order_by(*orderings.get(ordenacao, orderings['nome']))
    )


def garantir_linhas_pagamento_salario(controle: PagamentoSalarioControle) -> None:
    competencia = controle.competencia
    funcionario_ids = set(_get_funcionarios_para_vt(competencia).values_list('pk', flat=True))
    existentes = set(
        PagamentoSalarioLinha.objects.filter(controle=controle).values_list(
            'funcionario_id', flat=True
        )
    )
    criar = funcionario_ids - existentes
    if criar:
        funcionarios = _get_funcionarios_para_vt(competencia).filter(pk__in=criar)
        PagamentoSalarioLinha.objects.bulk_create(
            [
                PagamentoSalarioLinha(
                    controle=controle,
                    funcionario=funcionario,
                    valor=Decimal('0.00'),
                )
                for funcionario in funcionarios
            ]
        )
    orphan = existentes - funcionario_ids
    if orphan:
        PagamentoSalarioLinha.objects.filter(
            controle=controle,
            funcionario_id__in=orphan,
        ).delete()


def _clonar_linhas_pagamento_salario(destino, origem):
    linhas = origem.linhas.select_related('funcionario', 'conta_bancaria_empresa').order_by(
        'funcionario__nome',
        'id',
    )
    novas = [
        PagamentoSalarioLinha(
            controle=destino,
            funcionario=linha.funcionario,
            valor=linha.valor,
            conta_bancaria_empresa=linha.conta_bancaria_empresa,
        )
        for linha in linhas
    ]
    if novas:
        PagamentoSalarioLinha.objects.bulk_create(novas, batch_size=500)


def _dados_pix(funcionario) -> dict[str, str]:
    pix = (getattr(funcionario, 'pix', '') or '').strip()
    tipo = funcionario.get_tipo_pix_display() if getattr(funcionario, 'tipo_pix', '') else '—'
    banco = str(funcionario.banco) if getattr(funcionario, 'banco_id', None) else '—'
    return {
        'tipo': tipo,
        'chave': pix or '—',
        'banco': banco,
    }


def _banco_empresa_texto(linha: PagamentoSalarioLinha) -> str:
    conta = getattr(linha, 'conta_bancaria_empresa', None)
    if not conta:
        return '—'
    return str(conta)


def _contexto_linha_tabela(
    linha: PagamentoSalarioLinha,
    *,
    seq: int,
    competencia: Competencia,
) -> dict:
    func = linha.funcionario
    data_referencia = _month_bounds(competencia.ano, competencia.mes)[1]
    data_admissao = func.data_admissao.strftime('%d/%m/%Y') if func.data_admissao else '—'
    tempo_admissao = _fmt_tempo_desde_admissao(func.data_admissao, data_referencia)
    iniciais = ''.join(parte[0] for parte in (func.nome or '').split()[:2]).upper() or 'F'
    return {
        'linha': linha,
        'seq': seq,
        'funcionario': func,
        'funcionario_iniciais': iniciais,
        'funcao': str(func.cargo) if func.cargo_id else '—',
        'lotacao': str(func.lotacao) if func.lotacao_id else '—',
        'data_admissao_fmt': data_admissao,
        'tempo_admissao_fmt': tempo_admissao,
        'cpf': func.cpf or '—',
        'valor_fmt': _fmt_af_moeda(linha.valor),
        'dados_pix': _dados_pix(func),
        'banco_empresa': _banco_empresa_texto(linha),
    }


def _monta_linhas_tabela(competencia: Competencia, controle: PagamentoSalarioControle, qs):
    return [
        _contexto_linha_tabela(
            linha,
            seq=n,
            competencia=competencia,
        )
        for n, linha in enumerate(qs, start=1)
    ]


def _totais_pagamento_salario(controle: PagamentoSalarioControle) -> dict[str, str]:
    agg = controle.linhas.aggregate(total=Sum('valor'))
    total = agg['total'] if agg['total'] is not None else Decimal('0.00')
    return {
        'total_funcionarios': controle.linhas.count(),
        'total_pagar_fmt': _fmt_af_moeda(total),
    }


def limpar_dados_pagamento_salario(controle: PagamentoSalarioControle) -> int:
    return PagamentoSalarioLinha.objects.filter(controle=controle).update(
        valor=Decimal('0.00'),
        conta_bancaria_empresa=None,
    )


def _contexto_modal_linha(
    *,
    form: PagamentoSalarioLinhaForm,
    linha: PagamentoSalarioLinha,
    competencia: Competencia,
    controle: PagamentoSalarioControle,
) -> dict:
    return {
        'form': form,
        'linha': linha,
        'competencia': competencia,
        'controle': controle,
        'salario_cadastrado_fmt': _fmt_af_moeda(linha.funcionario.salario or 0),
    }


def _contexto_modal_controle(
    *,
    form: PagamentoSalarioControleForm,
    controle: PagamentoSalarioControle | None,
    competencia: Competencia,
    modo: str = 'editar',
    criacao_modo: str = '',
    origem_controle_pk: str = '',
    modo_resumo: str = '',
) -> dict:
    return {
        'form': form,
        'controle': controle,
        'competencia': competencia,
        'modo': modo,
        'criacao_modo': criacao_modo,
        'origem_controle_pk': origem_controle_pk,
        'modo_resumo': modo_resumo,
    }


@login_required
def modal_opcoes_criar_pagamento_salario(request, competencia_pk):
    competencia = _get_competencia_empresa(request, competencia_pk)
    controles_origem = list(_pagamentos_salario_anteriores(competencia))
    return render(
        request,
        'controles_rh/pagamento_salario/_modal_opcoes_criar_controle.html',
        {
            'competencia': competencia,
            'controles_origem': controles_origem,
        },
    )


@login_required
def gerar_pagamento_salario_competencia(request, competencia_pk):
    competencia = _get_competencia_empresa(request, competencia_pk)
    criacao_modo = _modo_criacao_pagamento(request)
    origem_controle_pk = _origem_pagamento_pk(request)

    if request.method == 'GET':
        if not criacao_modo or criacao_modo not in ('vazio', 'funcionarios', 'clonar'):
            return redirect_empresa(
                request,
                'controles_rh:modal_opcoes_criar_pagamento_salario',
                competencia_pk=competencia.pk,
            )
        if criacao_modo == 'clonar' and not _get_pagamento_origem_clone(
            request,
            competencia,
            origem_controle_pk,
        ):
            messages.error(request, 'Selecione uma planilha anterior para clonar.')
            return redirect_empresa(
                request,
                'controles_rh:modal_opcoes_criar_pagamento_salario',
                competencia_pk=competencia.pk,
            )

    origem_controle = (
        _get_pagamento_origem_clone(request, competencia, origem_controle_pk)
        if criacao_modo == 'clonar'
        else None
    )
    initial = {'nome': _titulo_padrao_pagamento_salario(competencia)}
    form = PagamentoSalarioControleForm(request.POST or None, initial=initial)

    if request.method == 'POST':
        if not criacao_modo:
            criacao_modo = 'funcionarios'
        if form.is_valid():
            modo = (
                criacao_modo
                if criacao_modo in ('vazio', 'funcionarios', 'clonar')
                else 'funcionarios'
            )
            if modo == 'clonar':
                origem_controle = _get_pagamento_origem_clone(
                    request,
                    competencia,
                    origem_controle_pk,
                )
                if not origem_controle:
                    messages.error(request, 'Selecione uma planilha anterior para clonar.')
                    return render(
                        request,
                        'controles_rh/pagamento_salario/_modal_dados_planilha.html',
                        _contexto_modal_controle(
                            form=form,
                            controle=None,
                            competencia=competencia,
                            modo='criar',
                            criacao_modo=criacao_modo,
                            origem_controle_pk=origem_controle_pk,
                        ),
                    )

            with transaction.atomic():
                controle = form.save(commit=False)
                controle.competencia = competencia
                controle.save()
                if modo == 'funcionarios':
                    garantir_linhas_pagamento_salario(controle)
                elif modo == 'clonar':
                    _clonar_linhas_pagamento_salario(controle, origem_controle)

            audit_controles_rh(
                request,
                'create',
                f'Pagamento de salário criado na competência {competencia.referencia}.',
                {
                    'competencia_id': competencia.pk,
                    'pagamento_salario_controle_id': controle.pk,
                    'modo': modo,
                },
            )
            messages.success(request, 'Pagamento de salário criado com sucesso.')

            url = reverse_empresa(
                request,
                'controles_rh:pagamento_salario_competencia',
                kwargs={'controle_pk': controle.pk},
            )
            if _is_htmx(request):
                response = HttpResponse(status=200)
                response['HX-Redirect'] = url
                return response
            return redirect(url)

    modo_resumo = {
        'vazio': 'Cria a planilha sem funcionários.',
        'funcionarios': 'Cria uma linha para cada funcionário ativo.',
        'clonar': 'Copia linhas, valores e banco empresa da planilha selecionada.',
    }.get(criacao_modo, '')
    return render(
        request,
        'controles_rh/pagamento_salario/_modal_dados_planilha.html',
        _contexto_modal_controle(
            form=form,
            controle=None,
            competencia=competencia,
            modo='criar',
            criacao_modo=criacao_modo,
            origem_controle_pk=origem_controle_pk,
            modo_resumo=modo_resumo,
        ),
    )


@login_required
def modal_pagamento_salario_controle(request, controle_pk):
    controle = _get_controle_pagamento_empresa(request, controle_pk)
    competencia = controle.competencia

    if request.method == 'POST':
        form = PagamentoSalarioControleForm(request.POST, instance=controle)
        if form.is_valid():
            controle = form.save()
            audit_controles_rh(
                request,
                'update',
                f'Dados do pagamento de salário atualizados — {competencia.referencia}.',
                {
                    'competencia_id': competencia.pk,
                    'pagamento_salario_controle_id': controle.pk,
                },
            )
            if _is_htmx(request):
                response = HttpResponse(status=204)
                response['HX-Trigger'] = json.dumps({
                    'pagamentoSalarioDadosSalvos': {
                        'nome': controle.nome_exibicao,
                    },
                })
                return response
            messages.success(request, 'Dados da planilha atualizados.')
            return redirect_empresa(
                request,
                'controles_rh:pagamento_salario_competencia',
                kwargs={'controle_pk': controle.pk},
            )
        return render(
            request,
            'controles_rh/pagamento_salario/_modal_dados_planilha.html',
            _contexto_modal_controle(
                form=form,
                controle=controle,
                competencia=competencia,
            ),
        )

    form = PagamentoSalarioControleForm(instance=controle)
    return render(
        request,
        'controles_rh/pagamento_salario/_modal_dados_planilha.html',
        _contexto_modal_controle(
            form=form,
            controle=controle,
            competencia=competencia,
        ),
    )


@login_required
@require_POST
def limpar_pagamento_salario_competencia(request, controle_pk):
    controle = _get_controle_pagamento_empresa(request, controle_pk)
    competencia = controle.competencia
    total_linhas = limpar_dados_pagamento_salario(controle)

    audit_controles_rh(
        request,
        'update',
        f'Dados do pagamento de salário limpos na competência {competencia.referencia}.',
        {
            'competencia_id': competencia.pk,
            'pagamento_salario_controle_id': controle.pk,
            'linhas_atualizadas': total_linhas,
        },
    )

    if _is_htmx(request):
        response = HttpResponse(status=204)
        response['HX-Trigger'] = json.dumps({'pagamentoSalarioTabelaAtualizada': {}})
        return response

    messages.success(request, 'Dados do pagamento de salário limpos.')
    return redirect_empresa(
        request,
        'controles_rh:pagamento_salario_competencia',
        kwargs={'controle_pk': controle.pk},
    )


@login_required
@require_POST
def excluir_pagamento_salario_competencia(request, controle_pk):
    controle = _get_controle_pagamento_empresa(request, controle_pk)
    competencia = controle.competencia
    controle_id = controle.pk
    nome = controle.nome_exibicao
    controle.delete()

    audit_controles_rh(
        request,
        'delete',
        f'Pagamento de salário excluído da competência {competencia.referencia}.',
        {'competencia_id': competencia.pk, 'pagamento_salario_controle_id': controle_id},
    )
    messages.success(request, f'{nome} excluído.')

    url = reverse_empresa(
        request,
        'controles_rh:detalhe_competencia',
        kwargs={'ano': competencia.ano, 'mes': competencia.mes},
    )
    if _is_htmx(request):
        response = HttpResponse(status=200)
        response['HX-Redirect'] = url
        return response
    return redirect(url)


@login_required
def modal_pagamento_salario_linha(request, controle_pk, linha_pk):
    controle = _get_controle_pagamento_empresa(request, controle_pk)
    competencia = controle.competencia
    linha = get_object_or_404(
        PagamentoSalarioLinha.objects.select_related(
            'funcionario',
            'funcionario__cargo',
            'funcionario__banco',
            'conta_bancaria_empresa',
        ),
        pk=linha_pk,
        controle=controle,
    )

    if request.method == 'POST':
        post = request.POST.copy()
        raw = post.get('valor', '')
        s = raw.strip() if isinstance(raw, str) else str(raw or '').strip()
        if s == '':
            post['valor'] = '0'
        elif ',' in s:
            post['valor'] = s.replace('.', '').replace(',', '.')
        else:
            post['valor'] = s
        form = PagamentoSalarioLinhaForm(post, instance=linha, empresa=competencia.empresa)
        if form.is_valid():
            form.save()
            audit_controles_rh(
                request,
                'update',
                f'Pagamento de salário atualizado ({linha.funcionario.nome}) — {competencia.referencia}.',
                {
                    'pagamento_salario_linha_id': linha.pk,
                    'pagamento_salario_controle_id': controle.pk,
                    'competencia_id': competencia.pk,
                },
            )
            if _is_htmx(request):
                response = HttpResponse(status=204)
                response['HX-Trigger'] = json.dumps({
                    'pagamentoSalarioModalSalvo': {},
                    'pagamentoSalarioTabelaAtualizada': {},
                })
                return response
            messages.success(request, 'Pagamento do funcionário atualizado.')
            return redirect_empresa(
                request,
                'controles_rh:pagamento_salario_competencia',
                kwargs={'controle_pk': controle.pk},
            )
        return render(
            request,
            'controles_rh/pagamento_salario/_modal_edicao_linha.html',
            _contexto_modal_linha(
                form=form,
                linha=linha,
                competencia=competencia,
                controle=controle,
            ),
        )

    form = PagamentoSalarioLinhaForm(instance=linha, empresa=competencia.empresa)
    return render(
        request,
        'controles_rh/pagamento_salario/_modal_edicao_linha.html',
        _contexto_modal_linha(
            form=form,
            linha=linha,
            competencia=competencia,
            controle=controle,
        ),
    )


@login_required
def pagamento_salario_competencia(request, controle_pk):
    controle = _get_controle_pagamento_empresa(request, controle_pk)
    competencia = controle.competencia
    empresa = competencia.empresa

    partial = request.GET.get('partial')
    ordenacao = _ordenacao_linhas(request.GET.get('ordenacao'))

    if partial == 'tabela':
        qs = _queryset_linhas(controle, ordenacao=ordenacao)
        linhas = _monta_linhas_tabela(competencia, controle, qs)
        return render(
            request,
            'controles_rh/pagamento_salario/_tabela.html',
            {
                'competencia': competencia,
                'controle': controle,
                'linhas': linhas,
                'ordenacao': ordenacao,
            },
        )
    if partial == 'totais':
        return render(
            request,
            'controles_rh/pagamento_salario/_totais.html',
            _totais_pagamento_salario(controle),
        )

    context = {
        'page_title': f'{controle.nome_exibicao} — {competencia.referencia}',
        'competencia': competencia,
        'controle': controle,
        'empresa': empresa,
        'ordenacao': ordenacao,
        **_totais_pagamento_salario(controle),
    }
    return render(request, 'controles_rh/pagamento_salario/detalhe.html', context)
