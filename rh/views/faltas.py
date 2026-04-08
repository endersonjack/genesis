from __future__ import annotations

from datetime import date, timedelta

from django.contrib import messages
from django.db.models import Count, Prefetch, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from auditoria.registry import audit_rh

from core.urlutils import reverse_empresa

from controles_rh.models import Competencia

from ..forms import FaltaFuncionarioForm
from ..models import FaltaFuncionario, Funcionario
from .base import _empresa_ativa_or_redirect


def _month_bounds(ano: int, mes: int) -> tuple[date, date]:
    inicio = date(ano, mes, 1)
    if mes == 12:
        prox = date(ano + 1, 1, 1)
    else:
        prox = date(ano, mes + 1, 1)
    fim = prox - timedelta(days=1)
    return inicio, fim


def _overlap_days(a_inicio: date, a_fim: date, b_inicio: date, b_fim: date) -> int:
    """
    Retorna a quantidade de dias (inclusive) de sobreposição entre [a_inicio,a_fim] e [b_inicio,b_fim].
    Assume datas válidas e a_inicio <= a_fim, b_inicio <= b_fim.
    """
    inicio = max(a_inicio, b_inicio)
    fim = min(a_fim, b_fim)
    if fim < inicio:
        return 0
    return (fim - inicio).days + 1


def faltas_home(request: HttpRequest) -> HttpResponse:
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para continuar.',
    )
    if redirect_response:
        return redirect_response

    hoje = date.today()
    ano = int(request.GET.get('ano') or hoje.year)
    mes = int(request.GET.get('mes') or hoje.month)
    inicio, fim = _month_bounds(ano, mes)

    faltas_qs = FaltaFuncionario.objects.filter(
        funcionario__empresa=empresa_ativa
    ).filter(
        Q(data_inicio__lte=fim) & Q(data_fim__gte=inicio)
    )

    funcionarios_com_registro = (
        Funcionario.objects.filter(empresa=empresa_ativa, faltas__in=faltas_qs)
        .annotate(
            total_faltas=Count('faltas', filter=Q(faltas__in=faltas_qs), distinct=True),
            total_justificadas=Count(
                'faltas',
                filter=Q(faltas__in=faltas_qs, faltas__tipo__in=['abonada', 'saude']),
                distinct=True,
            ),
            total_nao_justificadas=Count(
                'faltas',
                filter=Q(faltas__in=faltas_qs, faltas__tipo='nao_justificada'),
                distinct=True,
            ),
        )
        .select_related('cargo', 'lotacao')
        .order_by('nome')
        .distinct()
    )

    return render(
        request,
        'rh/faltas/home.html',
        {
            'ano': ano,
            'mes': mes,
            'competencia_label': f'{mes:02d}/{ano}',
            'funcionarios_com_registro': funcionarios_com_registro,
        },
    )


def faltas_home_competencia(request: HttpRequest, competencia_pk: int) -> HttpResponse:
    """
    Home de faltas vinculada a uma Competência do módulo de Gestão RH.
    Remove seleção manual de mês/ano: usa competencia.mes/ano.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para continuar.',
    )
    if redirect_response:
        return redirect_response

    competencia = get_object_or_404(
        Competencia.objects.select_related('empresa'),
        pk=competencia_pk,
        empresa=empresa_ativa,
    )

    inicio, fim = _month_bounds(competencia.ano, competencia.mes)

    faltas_qs = FaltaFuncionario.objects.filter(
        funcionario__empresa=empresa_ativa
    ).filter(
        Q(data_inicio__lte=fim) & Q(data_fim__gte=inicio)
    )

    funcionarios_com_registro = list(
        Funcionario.objects.filter(empresa=empresa_ativa, faltas__in=faltas_qs)
        .select_related('cargo', 'lotacao')
        .prefetch_related(
            Prefetch('faltas', queryset=faltas_qs.order_by('data_inicio', 'data_fim'), to_attr='faltas_competencia')
        )
        .order_by('nome')
        .distinct()
    )

    # Calcula dias por tipo dentro da competência (considera sobreposição).
    for f in funcionarios_com_registro:
        dias_justificadas = 0
        dias_nao_justificadas = 0
        for item in getattr(f, 'faltas_competencia', []) or []:
            if not item.data_inicio or not item.data_fim:
                continue
            dias = _overlap_days(item.data_inicio, item.data_fim, inicio, fim)
            if item.tipo in ('abonada', 'saude'):
                dias_justificadas += dias
            elif item.tipo == 'nao_justificada':
                dias_nao_justificadas += dias
        f.dias_justificadas = dias_justificadas
        f.dias_nao_justificadas = dias_nao_justificadas

    return render(
        request,
        'rh/faltas/home_competencia.html',
        {
            'competencia': competencia,
            'competencia_label': competencia.referencia,
            'funcionarios_com_registro': funcionarios_com_registro,
        },
    )


def faltas_busca_funcionarios(request: HttpRequest) -> HttpResponse:
    """
    Fragmento HTML com funcionários filtrados por nome/CPF/matrícula (mín. 2 caracteres).
    Destinado à tela de faltas.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para continuar.',
    )
    if redirect_response:
        return redirect_response

    q = (request.GET.get('q') or '').strip()
    muito_curto = len(q) < 2
    resultados = []

    if not muito_curto:
        qs = (
            Funcionario.objects.filter(empresa=empresa_ativa)
            .exclude(situacao_atual__in=['demitido', 'inativo'])
            .filter(
                Q(nome__icontains=q)
                | Q(cpf__icontains=q)
                | Q(matricula__icontains=q)
                | Q(pis__icontains=q)
            )
            .select_related('cargo', 'lotacao')
            .order_by('nome')
        )
        resultados = list(qs[:25])

    return render(
        request,
        'rh/faltas/partials/busca_resultados.html',
        {'resultados': resultados, 'q': q, 'muito_curto': muito_curto},
    )


def faltas_busca_funcionarios_competencia(request: HttpRequest, competencia_pk: int) -> HttpResponse:
    """
    Busca rápida (HTMX) para tela de faltas por competência.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para continuar.',
    )
    if redirect_response:
        return redirect_response

    competencia = get_object_or_404(
        Competencia,
        pk=competencia_pk,
        empresa=empresa_ativa,
    )

    q = (request.GET.get('q') or '').strip()
    muito_curto = len(q) < 2
    resultados = []

    if not muito_curto:
        qs = (
            Funcionario.objects.filter(empresa=empresa_ativa)
            .exclude(situacao_atual__in=['demitido', 'inativo'])
            .filter(
                Q(nome__icontains=q)
                | Q(cpf__icontains=q)
                | Q(matricula__icontains=q)
                | Q(pis__icontains=q)
            )
            .select_related('cargo', 'lotacao')
            .order_by('nome')
        )
        resultados = list(qs[:25])

    return render(
        request,
        'rh/faltas/partials/busca_resultados.html',
        {
            'resultados': resultados,
            'q': q,
            'muito_curto': muito_curto,
            'competencia': competencia,
        },
    )


def faltas_funcionario(request: HttpRequest, pk: int) -> HttpResponse:
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.',
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(
        Funcionario.objects.select_related('cargo', 'lotacao', 'empresa'),
        pk=pk,
        empresa=empresa_ativa,
    )

    faltas = list(funcionario.faltas.all().order_by('-data_inicio', '-criado_em'))
    total_registros = len(faltas)
    total_dias = 0
    dias_justificadas = 0
    dias_nao_justificadas = 0
    for item in faltas:
        if item.data_inicio and item.data_fim:
            dias = (item.data_fim - item.data_inicio).days + 1
            total_dias += dias
            if item.tipo in ('abonada', 'saude'):
                dias_justificadas += dias
            elif item.tipo == 'nao_justificada':
                dias_nao_justificadas += dias

    return render(
        request,
        'rh/faltas/funcionario.html',
        {
            'funcionario': funcionario,
            'faltas': faltas,
            'total_registros': total_registros,
            'total_dias': total_dias,
            'dias_justificadas': dias_justificadas,
            'dias_nao_justificadas': dias_nao_justificadas,
        },
    )


def faltas_funcionario_competencia(request: HttpRequest, competencia_pk: int, pk: int) -> HttpResponse:
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.',
    )
    if redirect_response:
        return redirect_response

    competencia = get_object_or_404(
        Competencia,
        pk=competencia_pk,
        empresa=empresa_ativa,
    )
    inicio, fim = _month_bounds(competencia.ano, competencia.mes)

    funcionario = get_object_or_404(
        Funcionario.objects.select_related('cargo', 'lotacao', 'empresa'),
        pk=pk,
        empresa=empresa_ativa,
    )

    faltas = list(funcionario.faltas.filter(
        Q(data_inicio__lte=fim) & Q(data_fim__gte=inicio)
    ).order_by('-data_inicio', '-criado_em'))

    total_registros = len(faltas)
    total_dias = 0
    dias_justificadas = 0
    dias_nao_justificadas = 0
    for item in faltas:
        if item.data_inicio and item.data_fim:
            dias = _overlap_days(item.data_inicio, item.data_fim, inicio, fim)
            total_dias += dias
            if item.tipo in ('abonada', 'saude'):
                dias_justificadas += dias
            elif item.tipo == 'nao_justificada':
                dias_nao_justificadas += dias

    return render(
        request,
        'rh/faltas/funcionario_competencia.html',
        {
            'competencia': competencia,
            'funcionario': funcionario,
            'faltas': faltas,
            'total_registros': total_registros,
            'total_dias': total_dias,
            'dias_justificadas': dias_justificadas,
            'dias_nao_justificadas': dias_nao_justificadas,
        },
    )


def modal_adicionar_falta(request: HttpRequest, pk: int) -> HttpResponse:
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.',
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(
        Funcionario,
        pk=pk,
        empresa=empresa_ativa,
    )

    if request.method == 'POST':
        form = FaltaFuncionarioForm(request.POST, request.FILES)
        if form.is_valid():
            falta: FaltaFuncionario = form.save(commit=False)
            falta.funcionario = funcionario
            falta.save()

            audit_rh(
                request,
                'criar_falta',
                f'Falta registrada para {funcionario.nome}.',
                {
                    'funcionario_id': funcionario.pk,
                    'falta_id': falta.pk,
                    'tipo': falta.tipo,
                    'data_inicio': str(falta.data_inicio),
                    'data_fim': str(falta.data_fim),
                    'ausencia_parcial': bool(falta.ausencia_parcial),
                    'ausencia_parcial_descricao': falta.ausencia_parcial_descricao,
                    'tem_anexo': bool(falta.anexo),
                },
            )

            messages.success(request, 'Falta registrada com sucesso.')
            res = HttpResponse('')
            res['HX-Redirect'] = reverse_empresa(
                request,
                'rh:faltas_funcionario',
                kwargs={'pk': funcionario.pk},
            )
            return res
    else:
        hoje = date.today()
        form = FaltaFuncionarioForm(
            initial={'data_inicio': hoje, 'data_fim': hoje}
        )

    return render(
        request,
        'rh/faltas/modals/modal_falta_form.html',
        {
            'modo': 'criar',
            'funcionario': funcionario,
            'form': form,
        },
    )


def modal_adicionar_falta_competencia(request: HttpRequest, competencia_pk: int, pk: int) -> HttpResponse:
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.',
    )
    if redirect_response:
        return redirect_response

    competencia = get_object_or_404(
        Competencia,
        pk=competencia_pk,
        empresa=empresa_ativa,
    )
    comp_inicio, comp_fim = _month_bounds(competencia.ano, competencia.mes)

    funcionario = get_object_or_404(
        Funcionario,
        pk=pk,
        empresa=empresa_ativa,
    )

    if request.method == 'POST':
        form = FaltaFuncionarioForm(request.POST, request.FILES)
        # limita input ao período da competência (HTML) + evita edição via devtools
        form.fields['data_inicio'].widget.attrs['min'] = comp_inicio.isoformat()
        form.fields['data_inicio'].widget.attrs['max'] = comp_fim.isoformat()
        form.fields['data_fim'].widget.attrs['min'] = comp_inicio.isoformat()
        form.fields['data_fim'].widget.attrs['max'] = comp_fim.isoformat()

        if form.is_valid():
            falta: FaltaFuncionario = form.save(commit=False)
            falta.funcionario = funcionario

            # Em competência: datas devem ficar dentro do mês/ano da competência
            if falta.data_inicio < comp_inicio or falta.data_inicio > comp_fim:
                form.add_error('data_inicio', f'Escolha uma data dentro da competência {competencia.referencia}.')
            if falta.data_fim < comp_inicio or falta.data_fim > comp_fim:
                form.add_error('data_fim', f'Escolha uma data dentro da competência {competencia.referencia}.')

            if not form.errors:
                falta.save()

                audit_rh(
                    request,
                    'criar_falta',
                    f'Falta registrada para {funcionario.nome}.',
                    {
                        'competencia_id': competencia.pk,
                        'competencia': competencia.referencia,
                        'funcionario_id': funcionario.pk,
                        'falta_id': falta.pk,
                        'tipo': falta.tipo,
                        'data_inicio': str(falta.data_inicio),
                        'data_fim': str(falta.data_fim),
                        'ausencia_parcial': bool(falta.ausencia_parcial),
                        'ausencia_parcial_descricao': falta.ausencia_parcial_descricao,
                        'tem_anexo': bool(falta.anexo),
                    },
                )

                messages.success(request, 'Falta registrada com sucesso.')
                res = HttpResponse('')
                res['HX-Redirect'] = reverse_empresa(
                    request,
                    'rh:faltas_funcionario_competencia',
                    kwargs={'competencia_pk': competencia.pk, 'pk': funcionario.pk},
                )
                return res
    else:
        hoje = date.today()
        if hoje < comp_inicio:
            hoje = comp_inicio
        if hoje > comp_fim:
            hoje = comp_fim
        form = FaltaFuncionarioForm(initial={'data_inicio': hoje, 'data_fim': hoje})
        form.fields['data_inicio'].widget.attrs['min'] = comp_inicio.isoformat()
        form.fields['data_inicio'].widget.attrs['max'] = comp_fim.isoformat()
        form.fields['data_fim'].widget.attrs['min'] = comp_inicio.isoformat()
        form.fields['data_fim'].widget.attrs['max'] = comp_fim.isoformat()

    return render(
        request,
        'rh/faltas/modals/modal_falta_form_competencia.html',
        {
            'modo': 'criar',
            'competencia': competencia,
            'comp_inicio': comp_inicio,
            'comp_fim': comp_fim,
            'funcionario': funcionario,
            'form': form,
        },
    )


def modal_editar_falta_competencia(
    request: HttpRequest,
    competencia_pk: int,
    pk: int,
    falta_id: int,
) -> HttpResponse:
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.',
    )
    if redirect_response:
        return redirect_response

    competencia = get_object_or_404(
        Competencia,
        pk=competencia_pk,
        empresa=empresa_ativa,
    )
    comp_inicio, comp_fim = _month_bounds(competencia.ano, competencia.mes)

    funcionario = get_object_or_404(
        Funcionario,
        pk=pk,
        empresa=empresa_ativa,
    )

    falta = get_object_or_404(
        FaltaFuncionario.objects.select_related('funcionario'),
        pk=falta_id,
        funcionario=funcionario,
    )

    if request.method == 'POST':
        form = FaltaFuncionarioForm(request.POST, request.FILES, instance=falta)
        form.fields['data_inicio'].widget.attrs['min'] = comp_inicio.isoformat()
        form.fields['data_inicio'].widget.attrs['max'] = comp_fim.isoformat()
        form.fields['data_fim'].widget.attrs['min'] = comp_inicio.isoformat()
        form.fields['data_fim'].widget.attrs['max'] = comp_fim.isoformat()

        if form.is_valid():
            falta_editada: FaltaFuncionario = form.save(commit=False)
            if falta_editada.data_inicio < comp_inicio or falta_editada.data_inicio > comp_fim:
                form.add_error('data_inicio', f'Escolha uma data dentro da competência {competencia.referencia}.')
            if falta_editada.data_fim < comp_inicio or falta_editada.data_fim > comp_fim:
                form.add_error('data_fim', f'Escolha uma data dentro da competência {competencia.referencia}.')

            if not form.errors:
                falta_editada.save()

                audit_rh(
                    request,
                    'editar_falta',
                    f'Falta editada para {funcionario.nome}.',
                    {
                        'competencia_id': competencia.pk,
                        'competencia': competencia.referencia,
                        'funcionario_id': funcionario.pk,
                        'falta_id': falta.pk,
                        'tipo': falta_editada.tipo,
                        'subtipo': falta_editada.subtipo,
                        'data_inicio': str(falta_editada.data_inicio),
                        'data_fim': str(falta_editada.data_fim),
                        'ausencia_parcial': bool(falta_editada.ausencia_parcial),
                        'ausencia_parcial_descricao': falta_editada.ausencia_parcial_descricao,
                        'tem_anexo': bool(falta_editada.anexo),
                    },
                )

                messages.success(request, 'Falta atualizada com sucesso.')
                res = HttpResponse('')
                res['HX-Redirect'] = reverse_empresa(
                    request,
                    'rh:faltas_funcionario_competencia',
                    kwargs={'competencia_pk': competencia.pk, 'pk': funcionario.pk},
                )
                return res
    else:
        form = FaltaFuncionarioForm(instance=falta)
        form.fields['data_inicio'].widget.attrs['min'] = comp_inicio.isoformat()
        form.fields['data_inicio'].widget.attrs['max'] = comp_fim.isoformat()
        form.fields['data_fim'].widget.attrs['min'] = comp_inicio.isoformat()
        form.fields['data_fim'].widget.attrs['max'] = comp_fim.isoformat()

    return render(
        request,
        'rh/faltas/modals/modal_falta_form_competencia.html',
        {
            'modo': 'editar',
            'competencia': competencia,
            'comp_inicio': comp_inicio,
            'comp_fim': comp_fim,
            'funcionario': funcionario,
            'falta': falta,
            'form': form,
        },
    )


def modal_excluir_falta_competencia(
    request: HttpRequest,
    competencia_pk: int,
    pk: int,
    falta_id: int,
) -> HttpResponse:
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.',
    )
    if redirect_response:
        return redirect_response

    competencia = get_object_or_404(
        Competencia,
        pk=competencia_pk,
        empresa=empresa_ativa,
    )

    funcionario = get_object_or_404(
        Funcionario,
        pk=pk,
        empresa=empresa_ativa,
    )

    falta = get_object_or_404(
        FaltaFuncionario.objects.select_related('funcionario'),
        pk=falta_id,
        funcionario=funcionario,
    )

    if request.method == 'POST':
        resumo = f'Falta excluída para {funcionario.nome}.'
        detalhes = {
            'competencia_id': competencia.pk,
            'competencia': competencia.referencia,
            'funcionario_id': funcionario.pk,
            'falta_id': falta.pk,
            'tipo': falta.tipo,
            'subtipo': falta.subtipo,
            'data_inicio': str(falta.data_inicio),
            'data_fim': str(falta.data_fim),
            'ausencia_parcial': bool(falta.ausencia_parcial),
            'tem_anexo': bool(falta.anexo),
        }
        falta.delete()

        audit_rh(request, 'excluir_falta', resumo, detalhes)
        messages.success(request, 'Falta excluída com sucesso.')
        res = HttpResponse('')
        res['HX-Redirect'] = reverse_empresa(
            request,
            'rh:faltas_funcionario_competencia',
            kwargs={'competencia_pk': competencia.pk, 'pk': funcionario.pk},
        )
        return res

    return render(
        request,
        'rh/faltas/modals/modal_falta_excluir_competencia.html',
        {
            'competencia': competencia,
            'funcionario': funcionario,
            'falta': falta,
        },
    )

