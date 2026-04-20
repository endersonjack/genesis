"""Relatórios consolidados de estoque (funcionário, ferramentas, itens, auditoria)."""
from __future__ import annotations

from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count, Prefetch, Q
from django.shortcuts import redirect, render
from django.utils import timezone

from auditoria.models import RegistroAuditoria

from core.urlutils import redirect_empresa, reverse_empresa

from rh.models import Funcionario

from .item_views import (
    _enriquecer_logs_movimentacao,
    _MOVIMENTAR_LOG_OPERACOES_EXCLUIDAS,
)
from .models import (
    Cautela,
    Entrega_Cautela,
    Ferramenta,
    Item,
    RequisicaoEstoque,
    RequisicaoEstoqueItem,
)
from .requisicoes_views import _empresa, _is_htmx

_SECOES_RELATORIO = frozenset({
    'funcionario',
    'funcionario_requisicao',
    'funcionario_ferramenta',
    'ferramenta',
    'item',
    'auditoria_movimentar',
    'auditoria_cautelas',
})

REL_PAGE = 30
# Auditoria (movimentar + cautelas): sempre no máximo 30 por página, inclusive no modo impressão.
REL_PAGE_AUDITORIA = 30
REL_PAGE_IMPRESSAO = 50_000

# Parâmetros de paginação da tela — removidos na URL de exportação PDF para gerar
# a lista completa (até REL_PAGE_IMPRESSAO) com os mesmos filtros.
_REL_EXPORT_POP_PAGES = (
    'req_func_page',
    'caut_func_page',
    'freq_det_page',
    'fferr_page',
    'ferr_linhas_page',
    'item_log_page',
    'log_page',
    'clog_page',
)


def _build_rel_export_queries(request) -> dict[str, str]:
    base = request.GET.copy()
    for k in _REL_EXPORT_POP_PAGES:
        base.pop(k, None)
    out: dict[str, str] = {}
    for sec in _SECOES_RELATORIO:
        q = base.copy()
        q['secao'] = sec
        out[sec] = q.urlencode()
    return out


def _rel_page_query(request, secao_val: str, *pop_keys: str) -> str:
    q = request.GET.copy()
    for k in pop_keys:
        q.pop(k, None)
    q['secao'] = secao_val
    return q.urlencode()

_CAUTELA_AUDIT_OP_LABEL = {
    'adiar_prazo': 'Prazo / previsão alterado',
    'entrega_completa': 'Devolução total registrada',
    'entrega_parcial': 'Devolução parcial registrada',
}


def _parse_date(s: str | None):
    if not (s or '').strip():
        return None
    try:
        return timezone.datetime.strptime(s.strip(), '%Y-%m-%d').date()
    except ValueError:
        return None


def _enriquecer_logs_cautela(request, empresa, logs_page_obj):
    if not logs_page_obj:
        return
    obj_list = getattr(logs_page_obj, 'object_list', None)
    if not obj_list:
        return
    cids = set()
    for log in obj_list:
        d = log.detalhes or {}
        raw = d.get('cautela_id')
        if raw is not None:
            try:
                cids.add(int(raw))
            except (TypeError, ValueError):
                pass
    existentes = set(
        Cautela.objects.filter(empresa=empresa, pk__in=cids).values_list('pk', flat=True)
    )
    for log in obj_list:
        d = log.detalhes or {}
        cid = d.get('cautela_id')
        log.cautela_pk = None
        log.cautela_url = None
        if cid is not None:
            try:
                pk = int(cid)
                log.cautela_pk = pk
                if pk in existentes:
                    log.cautela_url = reverse_empresa(
                        request,
                        'estoque:cautela_detalhe',
                        kwargs={'pk': pk},
                    )
            except (TypeError, ValueError):
                pass
        op = d.get('operacao')
        if op in _CAUTELA_AUDIT_OP_LABEL:
            log.cautela_op_label = _CAUTELA_AUDIT_OP_LABEL[op]
        elif op:
            log.cautela_op_label = str(op)
        else:
            log.cautela_op_label = '—'


@login_required
def autocomplete_funcionarios_relatorio(request):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')
    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:relatorios_estoque')
    q = (
        request.GET.get('q_func_rel') or request.GET.get('q') or ''
    ).strip()
    if len(q) < 2:
        return render(
            request,
            'estoque/requisicoes/_autocomplete_lista.html',
            {'items': [], 'hint': 'Digite pelo menos 2 caracteres.'},
        )
    items = list(
        Funcionario.objects.filter(empresa=empresa)
        .exclude(situacao_atual__in=['demitido', 'inativo'])
        .filter(nome__icontains=q)
        .order_by('nome')[:25]
    )
    return render(
        request,
        'estoque/requisicoes/_autocomplete_lista.html',
        {'items': items, 'hint': ''},
    )


@login_required
def autocomplete_ferramentas_relatorio(request):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')
    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:relatorios_estoque')
    q = (
        request.GET.get('q_ferr_rel')
        or request.GET.get('q_ferr_ff_filter')
        or request.GET.get('q')
        or ''
    ).strip()
    if len(q) < 2:
        return render(
            request,
            'estoque/requisicoes/_autocomplete_lista.html',
            {'items': [], 'hint': 'Digite pelo menos 2 caracteres.'},
        )
    items = list(
        Ferramenta.objects.filter(empresa=empresa, ativo=True)
        .filter(Q(descricao__icontains=q) | Q(marca__icontains=q))
        .order_by('descricao')[:25]
    )
    return render(
        request,
        'estoque/requisicoes/_autocomplete_lista.html',
        {'items': items, 'hint': ''},
    )


@login_required
def autocomplete_itens_relatorio(request):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')
    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:relatorios_estoque')
    q = (
        request.GET.get('q_item_rel')
        or request.GET.get('q_item_freq_det')
        or request.GET.get('q')
        or ''
    ).strip()
    if len(q) < 2:
        return render(
            request,
            'estoque/requisicoes/_autocomplete_lista.html',
            {'items': [], 'hint': 'Digite pelo menos 2 caracteres.'},
        )
    items = list(
        Item.objects.filter(empresa=empresa, ativo=True)
        .filter(Q(descricao__icontains=q) | Q(marca__icontains=q))
        .order_by('descricao')[:25]
    )
    return render(
        request,
        'estoque/requisicoes/_autocomplete_lista.html',
        {'items': items, 'hint': ''},
    )


def _relatorios_build_context(
    request,
    empresa,
    page_size: int,
    relatorios_page_url_name: str,
) -> dict:
    raw_secao = (request.GET.get('secao') or '').strip()
    secao_relat = raw_secao if raw_secao in _SECOES_RELATORIO else 'funcionario'

    # --- Funcionário ---
    func_raw = (request.GET.get('funcionario_id') or '').strip()
    func_id = None
    if func_raw.isdigit():
        func_id = int(func_raw)
    func_ini = _parse_date(request.GET.get('func_data_ini'))
    func_fim = _parse_date(request.GET.get('func_data_fim'))
    funcionario = None
    requisicoes_func_page = None
    cautelas_func_page = None
    requisicoes_func_query = ''
    cautelas_func_query = ''
    freq_det_page = None
    freq_det_query = ''
    freq_item_filter_id = None
    freq_item_filter = None
    func_ff_page = None
    func_ff_query = ''
    fferr_ferramenta_filter_id = None
    fferr_ferramenta_filter = None
    if func_id:
        funcionario = Funcionario.objects.filter(
            pk=func_id, empresa=empresa
        ).first()
        if not funcionario:
            messages.warning(request, 'Funcionário não encontrado nesta empresa.')
            func_id = None
        else:
            rq = (
                RequisicaoEstoque.objects.filter(
                    empresa=empresa, solicitante=funcionario
                )
                .select_related('local', 'obra')
                .annotate(n_itens=Count('itens', distinct=True))
            )
            if func_ini:
                rq = rq.filter(criado_em__date__gte=func_ini)
            if func_fim:
                rq = rq.filter(criado_em__date__lte=func_fim)
            rq = rq.order_by('-criado_em', '-pk')
            rp = Paginator(rq, page_size)
            rpn = request.GET.get('req_func_page') or 1
            try:
                requisicoes_func_page = rp.page(rpn)
            except PageNotAnInteger:
                requisicoes_func_page = rp.page(1)
            except EmptyPage:
                requisicoes_func_page = rp.page(rp.num_pages)
            requisicoes_func_query = _rel_page_query(
                request, 'funcionario', 'req_func_page'
            )

            cq = (
                Cautela.objects.filter(empresa=empresa, funcionario=funcionario)
                .select_related('local', 'obra')
                .annotate(n_ferramentas=Count('ferramentas', distinct=True))
            )
            if func_ini:
                cq = cq.filter(data_inicio_cautela__gte=func_ini)
            if func_fim:
                cq = cq.filter(data_inicio_cautela__lte=func_fim)
            cq = cq.order_by('-data_inicio_cautela', '-pk')
            cp = Paginator(cq, page_size)
            cpn = request.GET.get('caut_func_page') or 1
            try:
                cautelas_func_page = cp.page(cpn)
            except PageNotAnInteger:
                cautelas_func_page = cp.page(1)
            except EmptyPage:
                cautelas_func_page = cp.page(cp.num_pages)
            cautelas_func_query = _rel_page_query(
                request, 'funcionario', 'caut_func_page'
            )

            # --- Funcionário × Requisição (detalhe + itens) ---
            freq_item_raw = (
                request.GET.get('freq_item_id') or ''
            ).strip()
            freq_item_pk = (
                int(freq_item_raw) if freq_item_raw.isdigit() else None
            )
            if freq_item_pk is not None:
                freq_item_filter = Item.objects.filter(
                    pk=freq_item_pk, empresa=empresa
                ).first()
                if not freq_item_filter:
                    freq_item_pk = None
            else:
                freq_item_filter = None
            freq_item_filter_id = freq_item_pk

            _req_it_pref = Prefetch(
                'itens',
                queryset=(
                    RequisicaoEstoqueItem.objects.select_related(
                        'item', 'item__unidade_medida'
                    ).order_by('pk')
                ),
            )
            freq_det_rq = (
                RequisicaoEstoque.objects.filter(
                    empresa=empresa, solicitante=funcionario
                )
                .select_related('local', 'obra', 'almoxarife')
                .prefetch_related(_req_it_pref)
                .annotate(n_itens=Count('itens', distinct=True))
            )
            if func_ini:
                freq_det_rq = freq_det_rq.filter(criado_em__date__gte=func_ini)
            if func_fim:
                freq_det_rq = freq_det_rq.filter(criado_em__date__lte=func_fim)
            if freq_item_pk is not None:
                freq_det_rq = freq_det_rq.filter(
                    itens__item_id=freq_item_pk
                ).distinct()
            freq_det_rq = freq_det_rq.order_by('-criado_em', '-pk')
            fdp = Paginator(freq_det_rq, page_size)
            fdpn = request.GET.get('freq_det_page') or 1
            try:
                freq_det_page = fdp.page(fdpn)
            except PageNotAnInteger:
                freq_det_page = fdp.page(1)
            except EmptyPage:
                freq_det_page = fdp.page(fdp.num_pages)
            freq_det_query = _rel_page_query(
                request, 'funcionario_requisicao', 'freq_det_page'
            )

            # --- Funcionário × Ferramenta (retirada / devolução) ---
            fferr_filt_raw = (
                request.GET.get('fferr_ferramenta_id') or ''
            ).strip()
            fferr_filt_pk = (
                int(fferr_filt_raw) if fferr_filt_raw.isdigit() else None
            )
            fferr_filt_ferramenta = None
            if fferr_filt_pk is not None:
                fferr_filt_ferramenta = Ferramenta.objects.filter(
                    pk=fferr_filt_pk, empresa=empresa
                ).first()
                if not fferr_filt_ferramenta:
                    fferr_filt_pk = None
            fferr_ferramenta_filter_id = fferr_filt_pk
            fferr_ferramenta_filter = fferr_filt_ferramenta

            entregas_pref = Prefetch(
                'entregas',
                queryset=(
                    Entrega_Cautela.objects.select_related(
                        'motivo', 'situacao_ferramentas'
                    )
                    .prefetch_related('ferramentas_devolvidas')
                    .order_by('data_entrega', 'pk')
                ),
            )
            cautelas_ff = (
                Cautela.objects.filter(empresa=empresa, funcionario=funcionario)
                .select_related('local', 'obra')
                .prefetch_related('ferramentas', entregas_pref)
                .order_by('-data_inicio_cautela', '-pk')
            )
            if func_ini:
                cautelas_ff = cautelas_ff.filter(
                    data_inicio_cautela__gte=func_ini
                )
            if func_fim:
                cautelas_ff = cautelas_ff.filter(
                    data_inicio_cautela__lte=func_fim
                )
            if fferr_filt_pk is not None:
                cautelas_ff = cautelas_ff.filter(
                    Q(ferramentas__pk=fferr_filt_pk)
                    | Q(entregas__ferramentas_devolvidas=fferr_filt_pk)
                ).distinct()
            # Uma entrada por cautela: ativas, inativas (encerradas) e qualquer entrega
            # (não, parcial, total), sempre com a lista de ferramentas da cautela.
            func_ff_rows = []
            for cautela in cautelas_ff:
                ferr_list = list(
                    cautela.ferramentas.all().order_by('descricao', 'pk')
                )
                entregas_ordered = list(cautela.entregas.all())
                delivered_ids: set[int] = set()
                ferramentas_entregues = []
                for ent in entregas_ordered:
                    for f in ent.ferramentas_devolvidas.all():
                        if f.pk not in delivered_ids:
                            delivered_ids.add(f.pk)
                            ferramentas_entregues.append(f)
                ferramentas_ativas = [
                    f for f in ferr_list if f.pk not in delivered_ids
                ]
                func_ff_rows.append(
                    {
                        'cautela': cautela,
                        'retirada': cautela.data_inicio_cautela,
                        'ferramentas': ferr_list,
                        'entregas': entregas_ordered,
                        'ferramentas_entregues': ferramentas_entregues,
                        'ferramentas_ativas': ferramentas_ativas,
                    }
                )
            func_ff_rows.sort(
                key=lambda r: (r['retirada'] or date.min, r['cautela'].pk),
                reverse=True,
            )
            ffp = Paginator(func_ff_rows, page_size)
            ffpn = request.GET.get('fferr_page') or 1
            try:
                func_ff_page = ffp.page(ffpn)
            except PageNotAnInteger:
                func_ff_page = ffp.page(1)
            except EmptyPage:
                func_ff_page = ffp.page(ffp.num_pages)
            func_ff_query = _rel_page_query(
                request, 'funcionario_ferramenta', 'fferr_page'
            )

    # --- Ferramenta ---
    ferr_raw = (request.GET.get('ferramenta_id') or '').strip()
    ferr_id = int(ferr_raw) if ferr_raw.isdigit() else None
    ferr_ini = _parse_date(request.GET.get('ferr_data_ini'))
    ferr_fim = _parse_date(request.GET.get('ferr_data_fim'))
    ferramenta = None
    ferramenta_linhas_page = None
    ferr_linhas_query = ''
    if ferr_id:
        ferramenta = Ferramenta.objects.filter(pk=ferr_id, empresa=empresa).first()
        if not ferramenta:
            messages.warning(request, 'Ferramenta não encontrada.')
            ferr_id = None
        else:
            ferramenta_linhas = []
            hoje = timezone.now().date()
            ferr_pk = ferramenta.pk
            entregas_pref = Prefetch(
                'entregas',
                queryset=(
                    Entrega_Cautela.objects.select_related(
                        'motivo', 'situacao_ferramentas'
                    )
                    .prefetch_related('ferramentas_devolvidas')
                    .order_by('-data_entrega', '-pk')
                ),
            )
            # Inclui cautelas em que a ferramenta ainda está no M2M e cautelas em que
            # já foi devolvida (remove do M2M, mas permanece em entregas.ferramentas_devolvidas).
            cautelas_com_ferr = (
                Cautela.objects.filter(empresa=empresa)
                .filter(
                    Q(ferramentas=ferramenta)
                    | Q(entregas__ferramentas_devolvidas=ferramenta)
                )
                .select_related('funcionario', 'local', 'obra')
                .prefetch_related(entregas_pref, 'ferramentas')
                .distinct()
            )
            if ferr_ini:
                cautelas_com_ferr = cautelas_com_ferr.filter(
                    data_inicio_cautela__gte=ferr_ini
                )
            if ferr_fim:
                cautelas_com_ferr = cautelas_com_ferr.filter(
                    data_inicio_cautela__lte=ferr_fim
                )
            cautelas_com_ferr = cautelas_com_ferr.order_by(
                '-data_inicio_cautela', '-pk'
            )

            def _entrega_que_devolveu(
                cautela: Cautela, ferramenta_id: int
            ) -> Entrega_Cautela | None:
                # Prefetch ordena por data_entrega decrescente: primeira correspondência
                # é a devolução mais recente desta ferramenta nesta cautela.
                for ent in cautela.entregas.all():
                    dev_pks = {
                        f.pk for f in ent.ferramentas_devolvidas.all()
                    }
                    if ferramenta_id in dev_pks:
                        return ent
                return None

            for c in cautelas_com_ferr:
                di = c.data_inicio_cautela
                ainda_na_cautela = ferr_pk in {
                    f.pk for f in c.ferramentas.all()
                }
                ent = (
                    None
                    if ainda_na_cautela
                    else _entrega_que_devolveu(c, ferr_pk)
                )
                de = ent.data_entrega if ent else None
                if de is not None:
                    dias = max(0, (de - di).days)
                    situacao = 'Entregue'
                else:
                    dias = max(0, (hoje - di).days)
                    situacao = 'Ativa'
                motivo_txt = (
                    ent.motivo.nome
                    if ent and ent.motivo_id and ent.motivo
                    else ''
                )
                sit_pos_txt = (
                    ent.situacao_ferramentas.nome
                    if ent
                    and ent.situacao_ferramentas_id
                    and ent.situacao_ferramentas
                    else ''
                )
                ferramenta_linhas.append(
                    {
                        'cautela': c,
                        'data_inicio': di,
                        'data_entrega': de,
                        'periodo_dias': dias,
                        'situacao': situacao,
                        'funcionario_nome': c.funcionario.nome,
                        'motivo_entrega': motivo_txt,
                        'situacao_entregue': sit_pos_txt,
                        'entrega_reg': ent,
                    }
                )

            def _ferr_rel_sort_key(r: dict) -> tuple:
                de = r['data_entrega']
                di = r['data_inicio'] or date.min
                cid = r['cautela'].pk
                if de is None:
                    return (0, -di.toordinal(), -cid)
                return (1, -de.toordinal(), -cid)

            ferramenta_linhas.sort(key=_ferr_rel_sort_key)
            fp = Paginator(ferramenta_linhas, page_size)
            fpn = request.GET.get('ferr_linhas_page') or 1
            try:
                ferramenta_linhas_page = fp.page(fpn)
            except PageNotAnInteger:
                ferramenta_linhas_page = fp.page(1)
            except EmptyPage:
                ferramenta_linhas_page = fp.page(fp.num_pages)
            ferr_linhas_query = _rel_page_query(
                request, 'ferramenta', 'ferr_linhas_page'
            )

    # --- Item entradas/saídas (auditoria) ---
    item_raw = (request.GET.get('item_id') or '').strip()
    item_id = int(item_raw) if item_raw.isdigit() else None
    item_ini = _parse_date(request.GET.get('item_data_ini'))
    item_fim = _parse_date(request.GET.get('item_data_fim'))
    item_obj = None
    item_logs_page_obj = None
    item_log_query = ''
    if item_id:
        item_obj = Item.objects.filter(pk=item_id, empresa=empresa).first()
        if not item_obj:
            messages.warning(request, 'Item não encontrado.')
            item_id = None
        else:
            iqs = (
                RegistroAuditoria.objects.filter(
                    empresa=empresa,
                    modulo='estoque',
                    detalhes__has_key='operacao',
                )
                .exclude(
                    detalhes__operacao__in=_MOVIMENTAR_LOG_OPERACOES_EXCLUIDAS
                )
                .filter(detalhes__item_id=item_id)
                .select_related('usuario')
                .only(
                    'criado_em',
                    'usuario__username',
                    'usuario__nome_completo',
                    'detalhes',
                    'resumo',
                )
                .order_by('-criado_em')
            )
            if item_ini:
                iqs = iqs.filter(criado_em__date__gte=item_ini)
            if item_fim:
                iqs = iqs.filter(criado_em__date__lte=item_fim)
            ip = Paginator(iqs, page_size)
            pnum = request.GET.get('item_log_page') or 1
            try:
                item_logs_page_obj = ip.page(pnum)
            except PageNotAnInteger:
                item_logs_page_obj = ip.page(1)
            except EmptyPage:
                item_logs_page_obj = ip.page(ip.num_pages)
            _enriquecer_logs_movimentacao(request, empresa, item_logs_page_obj)
            iq = request.GET.copy()
            iq.pop('item_log_page', None)
            iq['secao'] = 'item'
            item_log_query = iq.urlencode()

    # --- Auditoria movimentar (global) ---
    log_busca = (request.GET.get('log_q') or '').strip()
    logs_qs = (
        RegistroAuditoria.objects.filter(
            empresa=empresa,
            modulo='estoque',
            detalhes__has_key='operacao',
        )
        .exclude(detalhes__operacao__in=_MOVIMENTAR_LOG_OPERACOES_EXCLUIDAS)
        .select_related('usuario')
        .only(
            'criado_em',
            'usuario__username',
            'usuario__nome_completo',
            'detalhes',
            'resumo',
        )
        .order_by('-criado_em')
    )
    if log_busca:
        item_pks = list(
            Item.objects.filter(empresa=empresa)
            .filter(
                Q(descricao__icontains=log_busca) | Q(marca__icontains=log_busca)
            )
            .values_list('pk', flat=True)
        )
        log_item_q = Q(detalhes__item_descricao__icontains=log_busca)
        if item_pks:
            log_item_q |= Q(detalhes__item_id__in=item_pks)
        logs_qs = logs_qs.filter(log_item_q)
    logs_paginator = Paginator(logs_qs, REL_PAGE_AUDITORIA)
    log_page_param = request.GET.get('log_page') or 1
    try:
        logs_page_obj = logs_paginator.page(log_page_param)
    except PageNotAnInteger:
        logs_page_obj = logs_paginator.page(1)
    except EmptyPage:
        logs_page_obj = logs_paginator.page(logs_paginator.num_pages)
    _enriquecer_logs_movimentacao(request, empresa, logs_page_obj)
    log_q = request.GET.copy()
    log_q.pop('log_page', None)
    log_q['secao'] = 'auditoria_movimentar'
    log_query = log_q.urlencode()

    # --- Auditoria cautelas ---
    clog_busca = (request.GET.get('clog_q') or '').strip()
    cqs = (
        RegistroAuditoria.objects.filter(
            empresa=empresa,
            modulo='estoque',
        )
        .filter(detalhes__has_key='cautela_id')
        .select_related('usuario')
        .only(
            'criado_em',
            'usuario__username',
            'usuario__nome_completo',
            'detalhes',
            'resumo',
            'acao',
        )
        .order_by('-criado_em')
    )
    if clog_busca:
        if clog_busca.isdigit():
            cqs = cqs.filter(detalhes__cautela_id=int(clog_busca))
        else:
            cqs = cqs.filter(resumo__icontains=clog_busca)
    cp = Paginator(cqs, REL_PAGE_AUDITORIA)
    cpnum = request.GET.get('clog_page') or 1
    try:
        cautela_logs_page_obj = cp.page(cpnum)
    except PageNotAnInteger:
        cautela_logs_page_obj = cp.page(1)
    except EmptyPage:
        cautela_logs_page_obj = cp.page(cp.num_pages)
    _enriquecer_logs_cautela(request, empresa, cautela_logs_page_obj)
    cq2 = request.GET.copy()
    cq2.pop('clog_page', None)
    cq2['secao'] = 'auditoria_cautelas'
    clog_query = cq2.urlencode()

    ctx = {
        'page_title': 'Relatórios de estoque',
        'rel_page': page_size,
        'rel_page_auditoria': REL_PAGE_AUDITORIA,
        'funcionario': funcionario,
        'funcionario_id': func_id,
        'func_data_ini': request.GET.get('func_data_ini') or '',
        'func_data_fim': request.GET.get('func_data_fim') or '',
        'requisicoes_func_page': requisicoes_func_page,
        'cautelas_func_page': cautelas_func_page,
        'requisicoes_func_query': requisicoes_func_query,
        'cautelas_func_query': cautelas_func_query,
        'freq_det_page': freq_det_page,
        'freq_det_query': freq_det_query,
        'freq_item_filter_id': freq_item_filter_id,
        'freq_item_filter': freq_item_filter,
        'func_ff_page': func_ff_page,
        'func_ff_query': func_ff_query,
        'fferr_ferramenta_filter_id': fferr_ferramenta_filter_id,
        'fferr_ferramenta_filter': fferr_ferramenta_filter,
        'ferramenta': ferramenta,
        'ferramenta_id': ferr_id,
        'ferr_data_ini': request.GET.get('ferr_data_ini') or '',
        'ferr_data_fim': request.GET.get('ferr_data_fim') or '',
        'ferramenta_linhas_page': ferramenta_linhas_page,
        'ferr_linhas_query': ferr_linhas_query,
        'item_obj': item_obj,
        'item_id': item_id,
        'item_data_ini': request.GET.get('item_data_ini') or '',
        'item_data_fim': request.GET.get('item_data_fim') or '',
        'item_logs_page_obj': item_logs_page_obj,
        'item_log_query': item_log_query,
        'logs_page_obj': logs_page_obj,
        'log_query': log_query,
        'log_busca': log_busca,
        'cautela_logs_page_obj': cautela_logs_page_obj,
        'clog_query': clog_query,
        'clog_busca': clog_busca,
        'secao_relat': secao_relat,
        'funcionario_ac_url': reverse_empresa(
            request, 'estoque:autocomplete_funcionarios_relatorio'
        ),
        'ferramenta_ac_url': reverse_empresa(
            request, 'estoque:autocomplete_ferramentas_relatorio'
        ),
        'item_ac_url': reverse_empresa(
            request, 'estoque:autocomplete_itens_relatorio'
        ),
        'relatorios_page_url_name': relatorios_page_url_name,
        'relatorios_get_query': request.GET.urlencode(),
        'rel_export_q': _build_rel_export_queries(request),
    }
    return ctx


@login_required
def relatorios_estoque(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    ctx = _relatorios_build_context(
        request, empresa, REL_PAGE, 'estoque:relatorios_estoque'
    )
    return render(request, 'estoque/relatorios_estoque.html', ctx)


@login_required
def relatorios_impressao(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    ctx = _relatorios_build_context(
        request, empresa, REL_PAGE_IMPRESSAO, 'estoque:relatorios_impressao'
    )
    ctx['page_title'] = 'Relatórios de estoque — impressão'
    ctx['relatorios_impressao_mode'] = True
    return render(request, 'estoque/relatorios_estoque.html', ctx)


@login_required
def relatorios_impressao_pdf(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    ctx = _relatorios_build_context(
        request, empresa, REL_PAGE_IMPRESSAO, 'estoque:relatorios_impressao'
    )
    from . import relatorios_pdf

    return relatorios_pdf.build_http_response(request, empresa, ctx)
