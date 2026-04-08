from __future__ import annotations

from collections import defaultdict
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

from controles_rh.forms import AlteracaoFolhaLinhaForm
from controles_rh.models import AlteracaoFolhaControle, AlteracaoFolhaLinha, Competencia
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
    """Horas: sempre ponto decimal e 2 casas (ex.: 5.00)."""
    try:
        d = Decimal(str(v))
    except (InvalidOperation, TypeError, ValueError):
        return '—'
    return f'{d.quantize(Decimal("0.01")):.2f}'


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


def _totais_alteracao_folha(competencia: Competencia) -> dict[str, str]:
    """Somas de todas as linhas da competência (formatadas para o topo da página)."""
    z = Decimal('0')
    qs = AlteracaoFolhaLinha.objects.filter(competencia=competencia)
    agg = qs.aggregate(
        th=Sum('hora_extra'),
        tf=Sum('horas_feriado'),
        ad=Sum('adicional'),
        pr=Sum('premio'),
        oa=Sum('outro_adicional'),
        ds=Sum('descontos'),
        od=Sum('outro_desconto'),
    )

    def nz(v):
        return v if v is not None else z

    th, tf = nz(agg['th']), nz(agg['tf'])
    ad, pr, oa = nz(agg['ad']), nz(agg['pr']), nz(agg['oa'])
    ds, od = nz(agg['ds']), nz(agg['od'])
    total_ad_rs = ad + pr + oa
    total_desc_rs = ds + od

    return {
        'total_hora_extra_fmt': _fmt_af_horas(th),
        'total_horas_feriado_fmt': _fmt_af_horas(tf),
        'total_adicionais_rs_fmt': _fmt_af_moeda(total_ad_rs),
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


def _fmt_celula_faltas(dias_no_mes: set[int]) -> str:
    dias = sorted(dias_no_mes)
    if not dias:
        return '—'
    inner = ','.join(str(d) for d in dias)
    return f'{len(dias)} ({inner})'


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
        .only('funcionario_id', 'tipo', 'data_inicio', 'data_fim')
    )
    buckets: dict[int, dict[str, set[int]]] = defaultdict(
        lambda: {'nj': set(), 'j': set()}
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
            buckets[f.funcionario_id][chave].add(cur.day)
            cur += timedelta(days=1)

    out: dict[int, tuple[str, str]] = {}
    for fid in funcionario_ids:
        b = buckets.get(fid)
        if not b:
            out[fid] = ('—', '—')
        else:
            out[fid] = (_fmt_celula_faltas(b['nj']), _fmt_celula_faltas(b['j']))
    return out


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
    orphan = existentes - funcionario_ids
    if orphan:
        AlteracaoFolhaLinha.objects.filter(
            competencia=competencia, funcionario_id__in=orphan
        ).delete()


def _queryset_linhas(competencia: Competencia):
    return (
        AlteracaoFolhaLinha.objects.filter(competencia=competencia)
        .select_related('funcionario', 'funcionario__cargo')
        .annotate(_dep_qtd=Count('funcionario__dependentes', distinct=True))
        .order_by('funcionario__nome', 'id')
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
    return {
        'linha': linha,
        'seq': seq,
        'funcionario': func,
        'funcao': str(func.cargo) if func.cargo_id else '—',
        'passagem_sim': bool(getattr(func, 'recebe_vale_transporte', False)),
        'salario_familia_txt': sf_txt,
        'faltas_nj': faltas_nj,
        'faltas_j': faltas_j,
        'hora_extra_fmt': _fmt_af_horas(linha.hora_extra),
        'horas_feriado_fmt': _fmt_af_horas(linha.horas_feriado),
        'adicional_fmt': _fmt_af_moeda(linha.adicional),
        'premio_fmt': _fmt_af_moeda(linha.premio),
        'outro_adicional_fmt': _fmt_af_moeda(linha.outro_adicional),
        'descontos_fmt': _fmt_af_moeda(linha.descontos),
        'outro_desconto_fmt': _fmt_af_moeda(linha.outro_desconto),
    }


def _faltas_texto_modal(linha: AlteracaoFolhaLinha, competencia: Competencia) -> dict[str, str]:
    m = _mapa_faltas_texto_por_funcionario(competencia, [linha.funcionario_id])
    nj, j = m.get(linha.funcionario_id, ('—', '—'))
    return {'faltas_nj': nj, 'faltas_j': j}


def _monta_linhas_tabela(competencia: Competencia, qs):
    linhas_list = list(qs)
    f_ids = [l.funcionario_id for l in linhas_list]
    faltas_map = _mapa_faltas_texto_por_funcionario(competencia, f_ids)
    deps_map = _deps_map_fallback(f_ids)
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

    if request.method == 'POST':
        post = request.POST.copy()
        for fname in AlteracaoFolhaLinhaForm.Meta.fields:
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
        if form.is_valid():
            form.save()
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
            'linha': linha,
            'competencia': competencia,
            **_faltas_texto_modal(linha, competencia),
        }
        return render(request, 'controles_rh/alteracao_folha/_modal_edicao_linha.html', ctx)

    form = AlteracaoFolhaLinhaForm(instance=linha)
    ctx = {
        'form': form,
        'linha': linha,
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

    garantir_linhas_alteracao_folha(competencia)

    if partial == 'tabela':
        qs = _queryset_linhas(competencia)
        linhas = _monta_linhas_tabela(competencia, qs)
        return render(
            request,
            'controles_rh/alteracao_folha/_tabela.html',
            {
                'competencia': competencia,
                'linhas': linhas,
            },
        )

    context = {
        'page_title': f'Alterações de folha — {competencia.referencia}',
        'competencia': competencia,
        'empresa': empresa,
        **_totais_alteracao_folha(competencia),
    }
    return render(request, 'controles_rh/alteracao_folha/detalhe.html', context)
