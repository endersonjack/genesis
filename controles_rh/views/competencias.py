import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from auditoria.registry import audit_controles_rh

from core.urlutils import redirect_empresa, reverse_empresa

from controles_rh.forms import CompetenciaForm
from controles_rh.models import (
    AlteracaoFolhaControle,
    AnexoDiversoCompetencia,
    CestaBasicaLista,
    Competencia,
    ControleCompetenciaOrdem,
    PagamentoSalarioControle,
    ValeTransporteTabela,
)

from rh.models import FaltaFuncionario
from rh.views.faltas import _month_bounds


def _is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def _get_empresa_ativa(request):
    """
    Retorna a empresa ativa do request.
    """
    return getattr(request, 'empresa_ativa', None)


def _get_competencia_empresa(request, pk):
    """
    Busca a competência restrita à empresa ativa.
    """
    empresa_ativa = _get_empresa_ativa(request)

    queryset = Competencia.objects.select_related('empresa')

    if empresa_ativa:
        queryset = queryset.filter(empresa=empresa_ativa)
    else:
        queryset = queryset.none()

    return get_object_or_404(queryset, pk=pk)


@login_required
def lista_competencias(request):
    """
    Lista as competências da empresa ativa.
    """
    empresa_ativa = _get_empresa_ativa(request)

    competencias = Competencia.objects.select_related('empresa')

    if empresa_ativa:
        competencias = competencias.filter(empresa=empresa_ativa)
    else:
        competencias = competencias.none()

    mes = request.GET.get('mes')
    ano = request.GET.get('ano')
    status = request.GET.get('status')

    if mes:
        try:
            competencias = competencias.filter(mes=int(mes))
        except ValueError:
            pass

    if ano:
        try:
            competencias = competencias.filter(ano=int(ano))
        except ValueError:
            pass

    if status == 'aberta':
        competencias = competencias.filter(fechada=False)
    elif status == 'fechada':
        competencias = competencias.filter(fechada=True)

    competencias = competencias.annotate(total_tabelas_vt=Count('tabelas_vt')).order_by(
        '-ano', '-mes', '-id'
    )

    context = {
        'page_title': 'Competências RH',
        'empresa_ativa': empresa_ativa,
        'competencias': competencias,
        'filtro_mes': mes or '',
        'filtro_ano': ano or '',
        'filtro_status': status or '',
        'meses': [
            (1, 'Janeiro'),
            (2, 'Fevereiro'),
            (3, 'Março'),
            (4, 'Abril'),
            (5, 'Maio'),
            (6, 'Junho'),
            (7, 'Julho'),
            (8, 'Agosto'),
            (9, 'Setembro'),
            (10, 'Outubro'),
            (11, 'Novembro'),
            (12, 'Dezembro'),
        ],
    }
    return render(request, 'controles_rh/competencias/lista.html', context)


@login_required
def criar_competencia(request):
    """
    Cria uma nova competência para a empresa ativa.
    """
    empresa_ativa = _get_empresa_ativa(request)

    if not empresa_ativa:
        messages.error(request, 'Selecione uma empresa ativa para criar a competência.')
        return redirect_empresa(request, 'controles_rh:home')

    form = CompetenciaForm(
        request.POST or None,
        empresa_ativa=empresa_ativa
    )

    if request.method == 'POST':
        if form.is_valid():
            competencia = form.save()
            audit_controles_rh(
                request,
                'create',
                f'Competência {competencia.referencia} criada.',
                {'competencia_id': competencia.pk},
            )
            messages.success(
                request,
                f'Competência {competencia.referencia} criada com sucesso.'
            )

            if _is_htmx(request):
                url = reverse_empresa(
                    request,
                    'controles_rh:detalhe_competencia',
                    kwargs={'ano': competencia.ano, 'mes': competencia.mes},
                )
                response = HttpResponse(status=200)
                response['HX-Redirect'] = url
                return response

            return redirect_empresa(
                request,
                'controles_rh:detalhe_competencia',
                kwargs={'ano': competencia.ano, 'mes': competencia.mes},
            )

        messages.error(request, 'Não foi possível criar a competência. Revise os campos.')

    context = {
        'page_title': 'Nova Competência',
        'titulo_pagina': 'Nova Competência',
        'empresa_ativa': empresa_ativa,
        'form': form,
        'competencia': None,
        'modo': 'criar',
    }

    return render(request, 'controles_rh/competencias/_form_modal.html', context)


def _ordenar_controles_competencia(competencia: Competencia, controles):
    if not controles:
        ControleCompetenciaOrdem.objects.filter(competencia=competencia).delete()
        return []

    chaves = [controle['chave'] for controle in controles]
    ordens_salvas = {
        item.chave: item.ordem
        for item in ControleCompetenciaOrdem.objects.filter(
            competencia=competencia,
            chave__in=chaves,
        )
    }
    novos_registros = []

    for indice, controle in enumerate(controles):
        ordem_padrao = (indice + 1) * 100
        ordem = ordens_salvas.get(controle['chave'])
        if ordem is None:
            ordem = ordem_padrao
            novos_registros.append(
                ControleCompetenciaOrdem(
                    competencia=competencia,
                    chave=controle['chave'],
                    ordem=ordem,
                )
            )

        controle['_ordem'] = ordem
        controle['_ordem_padrao'] = ordem_padrao

    if novos_registros:
        ControleCompetenciaOrdem.objects.bulk_create(
            novos_registros,
            ignore_conflicts=True,
        )

    ControleCompetenciaOrdem.objects.filter(
        competencia=competencia,
    ).exclude(chave__in=chaves).delete()

    return sorted(
        controles,
        key=lambda controle: (controle['_ordem'], controle['_ordem_padrao']),
    )


def _context_controles_da_competencia(competencia: Competencia, empresa):
    """
    Dados da coluna principal «Controles da Competência» (VT, Cesta, Faltas).
    Usado no fragmento HTMX; mantém consultas fora do render inicial da página.
    """
    tabelas_vt = ValeTransporteTabela.objects.filter(
        competencia=competencia
    ).order_by('ordem', 'nome', 'id')

    listas_cesta_basica = (
        CestaBasicaLista.objects.filter(competencia=competencia)
        .annotate(
            cb_total_ativos=Count('itens', filter=Q(itens__ativo=True)),
            cb_total_recebidos=Count(
                'itens', filter=Q(itens__ativo=True, itens__recebido=True)
            ),
        )
        .order_by('data_criacao', 'id')
    )

    inicio_mes, fim_mes = _month_bounds(competencia.ano, competencia.mes)
    faltas_na_competencia = FaltaFuncionario.objects.filter(
        funcionario__empresa=empresa,
    ).filter(Q(data_inicio__lte=fim_mes) & Q(data_fim__gte=inicio_mes))
    faltas_registros_count = faltas_na_competencia.count()
    faltas_colaboradores_count = (
        faltas_na_competencia.values('funcionario_id').distinct().count()
        if faltas_registros_count
        else 0
    )

    alteracao_folha_gerada = AlteracaoFolhaControle.objects.filter(
        competencia_id=competencia.pk
    ).exists()
    pagamentos_salario = PagamentoSalarioControle.objects.filter(
        competencia_id=competencia.pk
    ).order_by('data_geracao', 'id')
    pagamento_salario_gerado = pagamentos_salario.exists()

    anexos_diversos = AnexoDiversoCompetencia.objects.filter(
        competencia=competencia
    ).order_by('-data_criacao', '-id')

    controles_competencia = []
    if alteracao_folha_gerada:
        controles_competencia.append({
            'tipo': 'alteracao_folha',
            'chave': 'alteracao_folha',
        })
    for pagamento in pagamentos_salario:
        controles_competencia.append({
            'tipo': 'pagamento_salario',
            'chave': f'pagamento_salario:{pagamento.pk}',
            'pagamento': pagamento,
        })
    for tabela in tabelas_vt:
        controles_competencia.append({
            'tipo': 'vt',
            'chave': f'vt:{tabela.pk}',
            'tabela': tabela,
        })
    for lista_cb in listas_cesta_basica:
        controles_competencia.append({
            'tipo': 'cesta',
            'chave': f'cesta:{lista_cb.pk}',
            'lista_cb': lista_cb,
        })
    if faltas_registros_count:
        controles_competencia.append({
            'tipo': 'faltas',
            'chave': 'faltas',
        })
    for anexo in anexos_diversos:
        controles_competencia.append({
            'tipo': 'anexo',
            'chave': f'anexo:{anexo.pk}',
            'anexo': anexo,
        })

    controles_competencia = _ordenar_controles_competencia(
        competencia,
        controles_competencia,
    )

    return {
        'competencia': competencia,
        'alteracao_folha_gerada': alteracao_folha_gerada,
        'pagamento_salario_gerado': pagamento_salario_gerado,
        'pagamentos_salario': pagamentos_salario,
        'controles_competencia': controles_competencia,
        'tabelas_vt': tabelas_vt,
        'total_tabelas_vt': tabelas_vt.count(),
        'listas_cesta_basica': listas_cesta_basica,
        'anexos_diversos': anexos_diversos,
        'total_anexos_diversos': anexos_diversos.count(),
        'faltas_registros_count': faltas_registros_count,
        'faltas_colaboradores_count': faltas_colaboradores_count,
        'total_faltas': faltas_registros_count,
        'total_pagamentos': 0,
    }


@login_required
def detalhe_competencia(request, ano, mes):
    """
    Exibe os detalhes da competência como painel central dos controles.
    """
    empresa = getattr(request, 'empresa_ativa', None)

    competencia = get_object_or_404(
        Competencia,
        empresa=empresa,
        ano=ano,
        mes=mes
    )

    if _is_htmx(request) and request.GET.get('partial') == 'controles':
        ctx = _context_controles_da_competencia(competencia, empresa)
        return render(
            request,
            'controles_rh/competencias/_controles_da_competencia_body.html',
            ctx,
        )

    context = _context_controles_da_competencia(competencia, empresa)
    context.update(
        {
            'page_title': f'Competência {competencia.referencia}',
        }
    )
    return render(request, 'controles_rh/competencias/detalhe.html', context)


@login_required
@require_POST
def reordenar_controles_competencia(request, competencia_pk):
    competencia = _get_competencia_empresa(request, competencia_pk)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        payload = {}

    chaves = payload.get('ordem')
    if not isinstance(chaves, list):
        chaves = request.POST.getlist('ordem[]') or request.POST.getlist('ordem')

    chaves = [
        chave.strip()
        for chave in chaves
        if isinstance(chave, str) and chave.strip()
    ]

    if not chaves:
        return JsonResponse({'ok': False, 'erro': 'Nenhuma ordem enviada.'}, status=400)

    with transaction.atomic():
        for indice, chave in enumerate(dict.fromkeys(chaves), start=1):
            ControleCompetenciaOrdem.objects.update_or_create(
                competencia=competencia,
                chave=chave,
                defaults={'ordem': indice * 100},
            )

    return JsonResponse({'ok': True})


@login_required
def editar_competencia(request, pk):
    """
    Edita uma competência existente.
    """
    competencia = _get_competencia_empresa(request, pk)
    empresa_ativa = _get_empresa_ativa(request)

    form = CompetenciaForm(
        request.POST or None,
        instance=competencia,
        empresa_ativa=empresa_ativa
    )

    if request.method == 'POST':
        if form.is_valid():
            competencia = form.save()
            audit_controles_rh(
                request,
                'update',
                f'Competência {competencia.referencia} atualizada.',
                {'competencia_id': competencia.pk},
            )
            messages.success(
                request,
                f'Competência {competencia.referencia} atualizada com sucesso.'
            )

            if _is_htmx(request):
                url = reverse_empresa(
                    request,
                    'controles_rh:detalhe_competencia',
                    kwargs={'ano': competencia.ano, 'mes': competencia.mes},
                )
                response = HttpResponse(status=200)
                response['HX-Redirect'] = url
                return response

            return redirect_empresa(
                request,
                'controles_rh:detalhe_competencia',
                kwargs={'ano': competencia.ano, 'mes': competencia.mes},
            )

        messages.error(request, 'Não foi possível atualizar a competência. Revise os campos.')

    context = {
        'page_title': f'Editar Competência {competencia.referencia}',
        'titulo_pagina': f'Editar Competência {competencia.referencia}',
        'empresa_ativa': empresa_ativa,
        'form': form,
        'competencia': competencia,
        'modo': 'editar',
    }

    return render(request, 'controles_rh/competencias/_form_modal.html', context)


@login_required
def excluir_competencia(request, pk):
    """
    Exclui uma competência.
    """
    competencia = _get_competencia_empresa(request, pk)

    if request.method == 'POST':
        referencia = competencia.referencia
        cid = competencia.pk
        competencia.delete()
        audit_controles_rh(
            request,
            'delete',
            f'Competência {referencia} excluída.',
            {'competencia_id': cid},
        )
        messages.success(request, f'Competência {referencia} excluída com sucesso.')

        if _is_htmx(request):
            # Não usar HX-Refresh: recarregaria a URL atual (ex.: detalhe da competência) e daria 404.
            response = HttpResponse(status=200)
            response['HX-Redirect'] = reverse_empresa(request, 'controles_rh:home')
            return response

        return redirect_empresa(request, 'controles_rh:home')

    context = {
        'page_title': f'Excluir Competência {competencia.referencia}',
        'competencia': competencia,
    }

    return render(request, 'controles_rh/competencias/_excluir_modal.html', context)
