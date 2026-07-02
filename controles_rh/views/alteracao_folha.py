from __future__ import annotations

from collections import defaultdict
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from auditoria.registry import audit_controles_rh

from core.urlutils import redirect_empresa, reverse_empresa

from controles_rh.forms import AlteracaoFolhaLinhaForm, PremiacaoFuncionarioForm
from controles_rh.models import (
    AlteracaoFolhaControle,
    AlteracaoFolhaLinha,
    Competencia,
    PremiacaoFuncionario,
)
from controles_rh.views.vale_transporte import _get_funcionarios_para_vt
from rh.models import FaltaFuncionario, Funcionario


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


def _af_add_thousands_dot(int_digits: str) -> str:
    """Milhares com ponto (ex.: 1234 → 1.234)."""
    s = int_digits.lstrip('-+') or '0'
    parts: list[str] = []
    while s:
        parts.append(s[-3:])
        s = s[:-3]
    return '.'.join(reversed(parts))


def _fmt_af_horas(v) -> str:
    """Horas em horas/minutos (ex.: 1h30m)."""
    try:
        d = Decimal(str(v))
    except (InvalidOperation, TypeError, ValueError):
        return '—'
    if d < 0:
        return '—'
    total_minutos = int((d * Decimal('60')).quantize(Decimal('1')))
    horas, minutos = divmod(total_minutos, 60)
    return f'{horas}h{minutos:02d}m'


def _fmt_af_moeda(v) -> str:
    """Reais: milhares com ponto, centavos com vírgula (ex.: 1.234,56)."""
    try:
        d = Decimal(str(v))
    except (InvalidOperation, TypeError, ValueError):
        return '—'
    neg = d < 0
    d = abs(d.quantize(Decimal('0.01')))
    s = format(d, 'f')
    int_s, _, frac_s = s.partition('.')
    if not frac_s:
        frac_s = '00'
    return ('-' if neg else '') + _af_add_thousands_dot(int_s) + ',' + frac_s


def _fmt_af_percentual(v) -> str:
    valor = _fmt_af_moeda(v)
    if valor == '—':
        return valor
    return f'{valor}%'


def _totais_alteracao_folha(competencia: Competencia) -> dict[str, str]:
    """Somas de todas as linhas da competência (formatadas para o topo da página)."""
    z = Decimal('0')
    qs = AlteracaoFolhaLinha.objects.filter(competencia=competencia)
    agg = qs.aggregate(
        he=Sum('hora_extra'),
        hf=Sum('horas_feriado'),
        ad=Sum('adicional'),
        oa=Sum('outro_adicional'),
        ds=Sum('descontos'),
        od=Sum('outro_desconto'),
    )
    agg_prem = PremiacaoFuncionario.objects.filter(competencia=competencia).aggregate(
        pa=Sum('premio_atual'),
    )

    def nz(v):
        return v if v is not None else z

    oa = nz(agg['oa'])
    ds, od = nz(agg['ds']), nz(agg['od'])
    total_desc_rs = ds + od

    return {
        'total_hora_extra_fmt': _fmt_af_horas(nz(agg['he'])),
        'total_horas_feriado_fmt': _fmt_af_horas(nz(agg['hf'])),
        'total_outro_adicional_rs_fmt': _fmt_af_moeda(oa),
        'total_premiacao_atual_rs_fmt': _fmt_af_moeda(nz(agg_prem['pa'])),
        'total_descontos_rs_fmt': _fmt_af_moeda(total_desc_rs),
    }


def _month_bounds(ano: int, mes: int) -> tuple[date, date]:
    inicio = date(ano, mes, 1)
    if mes == 12:
        prox = date(ano + 1, 1, 1)
    else:
        prox = date(ano, mes + 1, 1)
    fim = prox - timedelta(days=1)
    return inicio, fim


def _fmt_celula_faltas(info: dict[str, object]) -> str:
    dias = sorted(info.get('dias', set()))
    parciais = list(info.get('parciais', []))
    if not dias and not parciais:
        return '—'
    partes: list[str] = []
    if dias:
        inner = ','.join(str(d) for d in dias)
        partes.append(f'{len(dias)} ({inner})')
    if parciais:
        grupos_parciais: dict[str, set[int]] = defaultdict(set)
        for parcial in parciais:
            descricao = str(parcial.get('descricao') or '').strip()
            grupos_parciais[descricao].add(parcial['dia'])

        for descricao, dias_parciais in sorted(
            grupos_parciais.items(),
            key=lambda item: (min(item[1]), item[0]),
        ):
            inner_parcial = ','.join(str(d) for d in sorted(dias_parciais))
            if descricao:
                partes.append(f'{descricao} parcial ({inner_parcial})')
            else:
                partes.append(f'parcial ({inner_parcial})')
    return ' + '.join(partes)


def _fmt_tempo_desde_admissao(data_admissao: date | None, data_referencia: date) -> str:
    if not data_admissao:
        return '—'
    if data_admissao > data_referencia:
        return '0 dias'

    anos = data_referencia.year - data_admissao.year
    meses = data_referencia.month - data_admissao.month
    dias = data_referencia.day - data_admissao.day

    if dias < 0:
        meses -= 1
        mes_anterior = data_referencia.month - 1
        ano_mes_anterior = data_referencia.year
        if mes_anterior == 0:
            mes_anterior = 12
            ano_mes_anterior -= 1
        dias += monthrange(ano_mes_anterior, mes_anterior)[1]

    if meses < 0:
        anos -= 1
        meses += 12

    partes = []
    if anos:
        partes.append(f'{anos} ano' + ('' if anos == 1 else 's'))
    if meses:
        partes.append(f'{meses} mês' + ('' if meses == 1 else 'es'))
    if dias or not partes:
        partes.append(f'{dias} dia' + ('' if dias == 1 else 's'))
    return ', '.join(partes)


def _mapa_faltas_texto_por_funcionario(
    competencia: Competencia, funcionario_ids: list[int]
) -> dict[int, tuple[str, str]]:
    """Uma consulta às faltas para todos os funcionários; evita N+1 na tabela."""
    if not funcionario_ids:
        return {}
    inicio_m, fim_m = _month_bounds(competencia.ano, competencia.mes)
    qs = (
        FaltaFuncionario.objects.filter(funcionario_id__in=funcionario_ids)
        .filter(Q(data_inicio__lte=fim_m) & Q(data_fim__gte=inicio_m))
        .only(
            'funcionario_id',
            'tipo',
            'data_inicio',
            'data_fim',
            'ausencia_parcial',
            'ausencia_parcial_descricao',
        )
    )
    buckets = defaultdict(
        lambda: {
            'nj': {'dias': set(), 'parciais': []},
            'j': {'dias': set(), 'parciais': []},
        }
    )
    for f in qs:
        if f.tipo == 'nao_justificada':
            chave = 'nj'
        elif f.tipo in ('abonada', 'saude'):
            chave = 'j'
        else:
            continue
        d0 = max(f.data_inicio, inicio_m)
        d1 = min(f.data_fim, fim_m)
        cur = d0
        while cur <= d1:
            if f.ausencia_parcial:
                buckets[f.funcionario_id][chave]['parciais'].append(
                    {
                        'dia': cur.day,
                        'descricao': f.ausencia_parcial_descricao,
                    }
                )
            else:
                buckets[f.funcionario_id][chave]['dias'].add(cur.day)
            cur += timedelta(days=1)

    out: dict[int, tuple[str, str]] = {}
    for fid in funcionario_ids:
        b = buckets.get(fid)
        if not b:
            out[fid] = ('—', '—')
        else:
            out[fid] = (_fmt_celula_faltas(b['nj']), _fmt_celula_faltas(b['j']))
    return out


def _queryset_competencias_anteriores(competencia: Competencia):
    return Competencia.objects.filter(empresa=competencia.empresa).filter(
        Q(ano__lt=competencia.ano) | Q(ano=competencia.ano, mes__lt=competencia.mes)
    )


def _defaults_premiacao_funcionario(
    competencia: Competencia,
    funcionario_id: int,
) -> dict[str, Decimal]:
    z = Decimal('0.00')
    anteriores = _queryset_competencias_anteriores(competencia)
    competencia_anterior = anteriores.order_by('-ano', '-mes', '-id').first()
    premio_anterior = z
    if competencia_anterior:
        premio_anterior = (
            PremiacaoFuncionario.objects.filter(
                competencia=competencia_anterior,
                funcionario_id=funcionario_id,
            )
            .values_list('premio_atual', flat=True)
            .first()
            or z
        )

    ultimos_premios = list(
        PremiacaoFuncionario.objects.filter(
            competencia__in=anteriores,
            funcionario_id=funcionario_id,
            premio_atual__gt=0,
        )
        .order_by('-competencia__ano', '-competencia__mes', '-competencia__id')
        .values_list('premio_atual', flat=True)[:3]
    )
    if ultimos_premios:
        media_premiacao = (sum(ultimos_premios, z) / Decimal(len(ultimos_premios))).quantize(
            Decimal('0.01')
        )
    else:
        media_premiacao = z

    return {
        'premio_anterior': premio_anterior,
        'media_premiacao': media_premiacao,
    }


def _nova_premiacao_funcionario(
    competencia: Competencia,
    funcionario_id: int,
) -> PremiacaoFuncionario:
    return PremiacaoFuncionario(
        competencia=competencia,
        funcionario_id=funcionario_id,
        **_defaults_premiacao_funcionario(competencia, funcionario_id),
    )


def _atualizar_premiacoes_automaticas(competencia: Competencia) -> None:
    premiacoes = PremiacaoFuncionario.objects.filter(competencia=competencia)
    for premiacao in premiacoes:
        defaults = _defaults_premiacao_funcionario(competencia, premiacao.funcionario_id)
        if (
            premiacao.premio_anterior == defaults['premio_anterior']
            and premiacao.media_premiacao == defaults['media_premiacao']
        ):
            continue
        PremiacaoFuncionario.objects.filter(pk=premiacao.pk).update(
            premio_anterior=defaults['premio_anterior'],
            media_premiacao=defaults['media_premiacao'],
        )


def garantir_linhas_alteracao_folha(competencia: Competencia) -> None:
    funcionario_ids = set(_get_funcionarios_para_vt(competencia).values_list('pk', flat=True))
    existentes = set(
        AlteracaoFolhaLinha.objects.filter(competencia=competencia).values_list(
            'funcionario_id', flat=True
        )
    )
    criar = funcionario_ids - existentes
    if criar:
        AlteracaoFolhaLinha.objects.bulk_create(
            [
                AlteracaoFolhaLinha(competencia=competencia, funcionario_id=fid)
                for fid in criar
            ]
        )
    premiacoes_existentes = set(
        PremiacaoFuncionario.objects.filter(competencia=competencia).values_list(
            'funcionario_id', flat=True
        )
    )
    criar_premiacoes = funcionario_ids - premiacoes_existentes
    if criar_premiacoes:
        PremiacaoFuncionario.objects.bulk_create(
            [
                _nova_premiacao_funcionario(competencia, fid)
                for fid in criar_premiacoes
            ]
        )
    orphan = existentes - funcionario_ids
    if orphan:
        AlteracaoFolhaLinha.objects.filter(
            competencia=competencia, funcionario_id__in=orphan
        ).delete()
    orphan_premiacoes = premiacoes_existentes - funcionario_ids
    if orphan_premiacoes:
        PremiacaoFuncionario.objects.filter(
            competencia=competencia, funcionario_id__in=orphan_premiacoes
        ).delete()
    _atualizar_premiacoes_automaticas(competencia)


def _ordenacao_linhas(valor: str | None) -> str:
    if valor in {'cargo', 'lotacao'}:
        return valor
    return 'nome'


def _queryset_linhas(competencia: Competencia, *, ordenacao: str = 'nome'):
    orderings = {
        'nome': ('funcionario__nome', 'id'),
        'cargo': ('funcionario__cargo__nome', 'funcionario__nome', 'id'),
        'lotacao': ('funcionario__lotacao__nome', 'funcionario__nome', 'id'),
    }
    return (
        AlteracaoFolhaLinha.objects.filter(competencia=competencia)
        .select_related('funcionario', 'funcionario__cargo', 'funcionario__lotacao')
        .annotate(_dep_qtd=Count('funcionario__dependentes', distinct=True))
        .order_by(*orderings.get(ordenacao, orderings['nome']))
    )


def _deps_map_fallback(funcionario_ids: list[int]) -> dict[int, int]:
    if not funcionario_ids:
        return {}
    return dict(
        Funcionario.objects.filter(pk__in=funcionario_ids)
        .annotate(dep_ct=Count('dependentes'))
        .values_list('pk', 'dep_ct')
    )


def _contexto_linha_tabela(
    linha: AlteracaoFolhaLinha,
    *,
    seq: int,
    competencia: Competencia,
    faltas_nj: str,
    faltas_j: str,
    premiacao: PremiacaoFuncionario | None = None,
    dep_qtd: int | None = None,
) -> dict:
    func = linha.funcionario
    if dep_qtd is None:
        dep_qtd = getattr(linha, '_dep_qtd', None)
    if dep_qtd is None:
        dep_qtd = func.dependentes.count()
    if getattr(func, 'recebe_salario_familia', False):
        sf_txt = str(dep_qtd)
    else:
        sf_txt = '—'
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
        'passagem_sim': bool(getattr(func, 'recebe_vale_transporte', False)),
        'salario_familia_txt': sf_txt,
        'faltas_nj': faltas_nj,
        'faltas_j': faltas_j,
        'hora_extra_fmt': _fmt_af_horas(linha.hora_extra),
        'horas_feriado_fmt': _fmt_af_horas(linha.horas_feriado),
        'adicional_fmt': _fmt_af_percentual(linha.adicional),
        'premio_atual_fmt': _fmt_af_moeda(premiacao.premio_atual if premiacao else 0),
        'premio_anterior_fmt': _fmt_af_moeda(premiacao.premio_anterior if premiacao else 0),
        'media_premiacao_fmt': _fmt_af_moeda(premiacao.media_premiacao if premiacao else 0),
        'outro_adicional_fmt': _fmt_af_moeda(linha.outro_adicional),
        'descontos_fmt': _fmt_af_moeda(linha.descontos),
        'outro_desconto_fmt': _fmt_af_moeda(linha.outro_desconto),
    }


def _faltas_texto_modal(linha: AlteracaoFolhaLinha, competencia: Competencia) -> dict[str, object]:
    m = _mapa_faltas_texto_por_funcionario(competencia, [linha.funcionario_id])
    nj, j = m.get(linha.funcionario_id, ('—', '—'))
    return {
        'faltas_nj': nj,
        'faltas_j': j,
        'tem_faltas_competencia': nj != '—' or j != '—',
    }


def _monta_linhas_tabela(competencia: Competencia, qs):
    linhas_list = list(qs)
    f_ids = [l.funcionario_id for l in linhas_list]
    faltas_map = _mapa_faltas_texto_por_funcionario(competencia, f_ids)
    deps_map = _deps_map_fallback(f_ids)
    premiacoes_map = {
        p.funcionario_id: p
        for p in PremiacaoFuncionario.objects.filter(
            competencia=competencia,
            funcionario_id__in=f_ids,
        )
    }
    out = []
    for n, linha in enumerate(linhas_list, start=1):
        dep_qtd = getattr(linha, '_dep_qtd', None)
        if dep_qtd is None:
            dep_qtd = deps_map.get(linha.funcionario_id, 0)
        fnj, fj = faltas_map.get(linha.funcionario_id, ('—', '—'))
        out.append(
            _contexto_linha_tabela(
                linha,
                seq=n,
                competencia=competencia,
                dep_qtd=dep_qtd,
                faltas_nj=fnj,
                faltas_j=fj,
                premiacao=premiacoes_map.get(linha.funcionario_id),
            )
        )
    return out


@login_required
@require_POST
def gerar_alteracao_folha_competencia(request, competencia_pk):
    competencia = _get_competencia_empresa(request, competencia_pk)

    with transaction.atomic():
        _, criado = AlteracaoFolhaControle.objects.get_or_create(competencia=competencia)
        if not criado:
            messages.info(request, 'A alteração de folha desta competência já está gerada.')
            url = reverse_empresa(
                request,
                'controles_rh:alteracao_folha_competencia',
                kwargs={'competencia_pk': competencia.pk},
            )
            if _is_htmx(request):
                response = HttpResponse(status=200)
                response['HX-Redirect'] = url
                return response
            return redirect(url)
        garantir_linhas_alteracao_folha(competencia)

    audit_controles_rh(
        request,
        'create',
        f'Alteração de folha gerada na competência {competencia.referencia}.',
        {'competencia_id': competencia.pk},
    )
    messages.success(request, 'Alteração de folha gerada com sucesso.')

    url = reverse_empresa(
        request,
        'controles_rh:alteracao_folha_competencia',
        kwargs={'competencia_pk': competencia.pk},
    )
    if _is_htmx(request):
        response = HttpResponse(status=200)
        response['HX-Redirect'] = url
        return response
    return redirect(url)


@login_required
@require_POST
def excluir_alteracao_folha_competencia(request, competencia_pk):
    competencia = _get_competencia_empresa(request, competencia_pk)

    with transaction.atomic():
        tinha = AlteracaoFolhaControle.objects.filter(competencia=competencia).exists()
        PremiacaoFuncionario.objects.filter(competencia=competencia).delete()
        AlteracaoFolhaLinha.objects.filter(competencia=competencia).delete()
        AlteracaoFolhaControle.objects.filter(competencia=competencia).delete()

    if tinha:
        audit_controles_rh(
            request,
            'delete',
            f'Alteração de folha excluída da competência {competencia.referencia}.',
            {'competencia_id': competencia.pk},
        )
        messages.success(request, 'Alteração de folha excluída. Você pode gerar novamente pelo botão +.')
    else:
        messages.info(request, 'Não havia alteração de folha para excluir.')

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
def modal_alteracao_folha_linha(request, competencia_pk, linha_pk):
    competencia = _get_competencia_empresa(request, competencia_pk)
    linha = get_object_or_404(
        AlteracaoFolhaLinha.objects.select_related('funcionario', 'funcionario__cargo'),
        pk=linha_pk,
        competencia=competencia,
    )
    premiacao, _ = PremiacaoFuncionario.objects.get_or_create(
        competencia=competencia,
        funcionario=linha.funcionario,
        defaults=_defaults_premiacao_funcionario(competencia, linha.funcionario_id),
    )

    if request.method == 'POST':
        post = request.POST.copy()
        for fname in [
            *AlteracaoFolhaLinhaForm.Meta.fields,
            *PremiacaoFuncionarioForm.Meta.fields,
        ]:
            raw = post.get(fname, '')
            s = raw.strip() if isinstance(raw, str) else str(raw or '').strip()
            if s == '':
                post[fname] = '0'
            elif ',' in s:
                # Fallback se o JS não normalizou (ex.: formato 1.234,56)
                post[fname] = s.replace('.', '').replace(',', '.')
            else:
                post[fname] = s
        form = AlteracaoFolhaLinhaForm(post, instance=linha)
        premiacao_form = PremiacaoFuncionarioForm(post, instance=premiacao)
        if form.is_valid() and premiacao_form.is_valid():
            with transaction.atomic():
                form.save()
                premiacao_form.save()
            audit_controles_rh(
                request,
                'update',
                f'Linha de alteração de folha atualizada ({linha.funcionario.nome}) — {competencia.referencia}.',
                {'alteracao_folha_linha_id': linha.pk, 'competencia_id': competencia.pk},
            )
            messages.success(request, 'Valores da linha atualizados.')
            url = reverse_empresa(
                request,
                'controles_rh:alteracao_folha_competencia',
                kwargs={'competencia_pk': competencia.pk},
            )
            response = HttpResponse(status=200)
            response['HX-Redirect'] = url
            return response
        ctx = {
            'form': form,
            'premiacao_form': premiacao_form,
            'linha': linha,
            'premiacao': premiacao,
            'competencia': competencia,
            **_faltas_texto_modal(linha, competencia),
        }
        return render(request, 'controles_rh/alteracao_folha/_modal_edicao_linha.html', ctx)

    form = AlteracaoFolhaLinhaForm(instance=linha)
    premiacao_form = PremiacaoFuncionarioForm(instance=premiacao)
    ctx = {
        'form': form,
        'premiacao_form': premiacao_form,
        'linha': linha,
        'premiacao': premiacao,
        'competencia': competencia,
        **_faltas_texto_modal(linha, competencia),
    }
    return render(request, 'controles_rh/alteracao_folha/_modal_edicao_linha.html', ctx)


@login_required
def alteracao_folha_competencia(request, competencia_pk):
    competencia = _get_competencia_empresa(request, competencia_pk)
    empresa = competencia.empresa

    if not AlteracaoFolhaControle.objects.filter(competencia=competencia).exists():
        messages.warning(
            request,
            'Gere a alteração de folha pelo botão + na competência antes de abrir a tabela.',
        )
        return redirect_empresa(
            request,
            'controles_rh:detalhe_competencia',
            kwargs={'ano': competencia.ano, 'mes': competencia.mes},
        )

    partial = request.GET.get('partial')
    ordenacao = _ordenacao_linhas(request.GET.get('ordenacao'))

    garantir_linhas_alteracao_folha(competencia)

    if partial == 'tabela':
        qs = _queryset_linhas(competencia, ordenacao=ordenacao)
        linhas = _monta_linhas_tabela(competencia, qs)
        return render(
            request,
            'controles_rh/alteracao_folha/_tabela.html',
            {
                'competencia': competencia,
                'linhas': linhas,
                'ordenacao': ordenacao,
            },
        )

    context = {
        'page_title': f'Alterações de folha — {competencia.referencia}',
        'competencia': competencia,
        'empresa': empresa,
        'ordenacao': ordenacao,
        **_totais_alteracao_folha(competencia),
    }
    return render(request, 'controles_rh/alteracao_folha/detalhe.html', context)
