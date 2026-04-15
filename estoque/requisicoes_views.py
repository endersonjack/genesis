from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from auditoria.models import RegistroAuditoria
from auditoria.registry import registrar_auditoria
from core.urlutils import is_safe_internal_path, redirect_empresa, reverse_empresa

from .item_views import _empresa  # reaproveita helper do módulo
from local.models import Local
from obras.models import Obra
from rh.models import Funcionario

from .models import CategoriaItem, Item, RequisicaoEstoque, RequisicaoEstoqueItem
from .requisicao_export import build_requisicao_pdf_bytes
from .requisicoes_forms import (
    RequisicaoEstoqueForm,
    RequisicaoEstoqueItemFormSet,
    RequisicaoEstoqueItemFormSetEdit,
)


_HISTORICO_REQ_OPERACAO_LABEL = {
    'criar_requisicao': 'Criação da requisição',
    'retirar': 'Retirada (estoque)',
    'ajuste_por_edicao_requisicao': 'Ajuste de quantidade (edição)',
    'ajustar_quantidade': 'Ajuste de quantidade',
    'devolver_total': 'Devolução total',
    'devolver_parcial': 'Devolução parcial',
    'devolver': 'Devolução',
    'devolver_por_exclusao_requisicao': 'Devolução (exclusão da requisição)',
    'devolver_por_cancelamento_requisicao': 'Devolução (cancelamento da requisição)',
    'cancelar_requisicao': 'Cancelamento da requisição',
    'editar_cabecalho': 'Alteração dos dados da requisição',
}


def _tipo_evento_historico_requisicao(reg: RegistroAuditoria) -> str:
    d = reg.detalhes or {}
    op = d.get('operacao')
    if op and op in _HISTORICO_REQ_OPERACAO_LABEL:
        return _HISTORICO_REQ_OPERACAO_LABEL[op]
    if reg.acao == 'delete':
        return 'Exclusão da requisição (registro legado)'
    return reg.get_acao_display()


def _historico_requisicao_qs(empresa, requisicao_id: int):
    return (
        RegistroAuditoria.objects.filter(
            empresa=empresa,
            modulo='estoque',
            detalhes__requisicao_id=requisicao_id,
        )
        .select_related('usuario')
        .order_by('-criado_em')
    )


def _bind_formset_empresa(formset, empresa):
    """Ajusta querysets dos selects do formset para a empresa."""
    qs_items = (
        Item.objects.filter(empresa=empresa, ativo=True)
        .select_related('unidade_medida')
        .order_by('descricao')
    )
    for f in getattr(formset, 'forms', []):
        if 'item' in f.fields:
            f.fields['item'].queryset = qs_items
    if hasattr(formset, 'empty_form') and 'item' in formset.empty_form.fields:
        formset.empty_form.fields['item'].queryset = qs_items


def _is_htmx(request) -> bool:
    v = request.headers.get('HX-Request')
    if v is None:
        v = request.META.get('HTTP_HX_REQUEST')
    return str(v).lower() == 'true'


def _wants_json(request) -> bool:
    accept = request.headers.get('Accept') or ''
    return 'application/json' in accept


def _parse_date_get(request, key: str, default):
    raw = (request.GET.get(key) or '').strip()
    if not raw:
        return default
    try:
        return timezone.datetime.strptime(raw, '%Y-%m-%d').date()
    except ValueError:
        return default


def _next_path_requisicao(request) -> str | None:
    raw = (request.GET.get('next') or request.POST.get('next') or '').strip()
    if not raw or not is_safe_internal_path(raw):
        return None
    return raw


def _redirect_requisicao_contexto(request, padrao_viewname: str, padrao_kwargs: dict | None = None):
    nxt = _next_path_requisicao(request)
    if nxt:
        return redirect(nxt)
    return redirect_empresa(request, padrao_viewname, kwargs=padrao_kwargs or {})


def _htmx_redirect(response: HttpResponse, path: str) -> HttpResponse:
    response['HX-Redirect'] = path
    return response


def _requisicoes_lista_inclui_canceladas(request) -> bool:
    """Administrador da empresa (ou superuser) vê também requisições canceladas na lista."""
    return bool(
        getattr(request, 'usuario_admin_empresa', False)
        or getattr(request.user, 'is_superuser', False)
    )


@login_required
def lista_requisicoes(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    hoje = timezone.localdate()
    data_inicio = _parse_date_get(request, 'data_inicio', hoje)
    data_fim = _parse_date_get(request, 'data_fim', hoje)
    legacy_data = (request.GET.get('data') or '').strip()
    if legacy_data and 'data_inicio' not in request.GET and 'data_fim' not in request.GET:
        try:
            d_legacy = timezone.datetime.strptime(legacy_data, '%Y-%m-%d').date()
            data_inicio = data_fim = d_legacy
        except ValueError:
            pass
    if data_inicio > data_fim:
        data_fim = data_inicio

    filtro_sol_raw = (request.GET.get('solicitante') or '').strip()
    filtro_loc_raw = (request.GET.get('local') or '').strip()
    filtro_obr_raw = (request.GET.get('obra') or '').strip()

    solicitante_sel = int(filtro_sol_raw) if filtro_sol_raw.isdigit() else None
    local_sel = int(filtro_loc_raw) if filtro_loc_raw.isdigit() else None
    obra_sel = int(filtro_obr_raw) if filtro_obr_raw.isdigit() else None

    qs = (
        RequisicaoEstoque.objects.filter(empresa=empresa)
        .select_related('solicitante', 'local', 'obra', 'almoxarife')
        .prefetch_related('itens__item', 'itens__item__unidade_medida')
        .order_by('-criado_em')
    )
    if not _requisicoes_lista_inclui_canceladas(request):
        qs = qs.filter(status=RequisicaoEstoque.Status.ATIVA)
    qs = qs.filter(criado_em__date__gte=data_inicio, criado_em__date__lte=data_fim)

    if solicitante_sel is not None:
        qs = qs.filter(solicitante_id=solicitante_sel)
    if local_sel is not None:
        qs = qs.filter(local_id=local_sel)
    if obra_sel is not None:
        qs = qs.filter(obra_id=obra_sel)

    requisicoes_por_pagina = 20
    paginator = Paginator(qs, requisicoes_por_pagina)
    page_param = request.GET.get('page') or 1
    try:
        page_obj = paginator.page(page_param)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    qparams = request.GET.copy()
    qparams.pop('page', None)
    query_sem_page = qparams.urlencode()

    solicitantes_opts = (
        Funcionario.objects.filter(empresa=empresa)
        .exclude(situacao_atual__in=['demitido', 'inativo'])
        .order_by('nome')
    )
    locais_opts = Local.objects.filter(empresa=empresa).order_by('nome')
    obras_opts = (
        Obra.objects.filter(empresa=empresa)
        .filter(Q(data_fim__isnull=True) | Q(data_fim__gte=hoje))
        .order_by('nome')
    )

    buscar_anteriores_query = urlencode(
        {
            'data_inicio': (hoje - timedelta(days=30)).strftime('%Y-%m-%d'),
            'data_fim': hoje.strftime('%Y-%m-%d'),
        }
    )

    return render(
        request,
        'estoque/requisicoes/lista.html',
        {
            'page_title': 'Requisições',
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'solicitante_sel': solicitante_sel,
            'local_sel': local_sel,
            'obra_sel': obra_sel,
            'solicitantes_opts': solicitantes_opts,
            'locais_opts': locais_opts,
            'obras_opts': obras_opts,
            'page_obj': page_obj,
            'query_sem_page': query_sem_page,
            'buscar_anteriores_query': buscar_anteriores_query,
            'requisicoes_lista_inclui_canceladas': _requisicoes_lista_inclui_canceladas(
                request
            ),
        },
    )


@login_required
def modal_requisicao_itens(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:requisicoes')

    req_qs = RequisicaoEstoque.objects.select_related('solicitante', 'local', 'obra')
    if not _requisicoes_lista_inclui_canceladas(request):
        req_qs = req_qs.filter(status=RequisicaoEstoque.Status.ATIVA)
    req = get_object_or_404(req_qs, pk=pk, empresa=empresa)
    itens = list(
        req.itens.select_related('item', 'item__unidade_medida')
        .prefetch_related('item__imagens')
        .order_by('item__descricao')
    )
    return render(
        request,
        'estoque/requisicoes/modal_requisicao_itens.html',
        {
            'requisicao': req,
            'itens_requisicao': itens,
        },
    )


@login_required
def detalhe_requisicao(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item_qs = (
        RequisicaoEstoqueItem.objects.select_related('item__categoria', 'item__unidade_medida')
        .prefetch_related('item__imagens')
        .order_by('item__descricao')
    )
    req = get_object_or_404(
        RequisicaoEstoque.objects.select_related('solicitante', 'local', 'obra', 'almoxarife').prefetch_related(
            Prefetch('itens', queryset=item_qs)
        ),
        pk=pk,
        empresa=empresa,
    )
    itens = list(req.itens.all())
    historico_regs = list(_historico_requisicao_qs(empresa, req.pk)[:150])
    historico_requisicao = [
        {'reg': r, 'tipo': _tipo_evento_historico_requisicao(r)} for r in historico_regs
    ]
    return render(
        request,
        'estoque/requisicoes/detalhe.html',
        {
            'page_title': f'Requisição #{req.pk}',
            'requisicao': req,
            'itens_requisicao': itens,
            'historico_requisicao': historico_requisicao,
        },
    )


@login_required
def editar_requisicao(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item_edit_qs = (
        RequisicaoEstoqueItem.objects.select_related('item__categoria', 'item__unidade_medida')
        .prefetch_related('item__imagens')
        .order_by('pk')
    )
    req = get_object_or_404(
        RequisicaoEstoque.objects.select_related('solicitante', 'local', 'obra', 'almoxarife').prefetch_related(
            Prefetch('itens', queryset=item_edit_qs)
        ),
        pk=pk,
        empresa=empresa,
    )
    if req.status != RequisicaoEstoque.Status.ATIVA:
        messages.warning(request, 'Requisições canceladas não podem ser editadas.')
        return redirect_empresa(request, 'estoque:detalhe_requisicao', kwargs={'pk': req.pk})
    draft_key = f'genesis:estoque:editar_requisicao:{req.pk}:v1'
    clear_key = f'genesis:estoque:editar_requisicao:{req.pk}:clear_next'

    if request.method == 'POST':
        form = RequisicaoEstoqueForm(request.POST, instance=req, empresa=empresa)
        formset = RequisicaoEstoqueItemFormSetEdit(
            request.POST,
            instance=req,
            prefix='itens',
        )
        _bind_formset_empresa(formset, empresa)

        if not form.is_valid() or not formset.is_valid():
            messages.error(request, 'Revise os campos e itens informados.')
        else:
            existentes = {
                ri.pk: {
                    'item_id': ri.item_id,
                    'qtd': ri.quantidade or Decimal('0'),
                }
                for ri in req.itens.all()
            }

            deltas_por_item: dict[int, Decimal] = {}
            itens_ativos: set[int] = set()
            linhas_ativas = 0
            erro_itens = False

            for f in formset.forms:
                cd = getattr(f, 'cleaned_data', None)
                if not cd:
                    continue

                inst = f.instance
                if cd.get('DELETE'):
                    if inst.pk:
                        snap = existentes.get(inst.pk)
                        if snap:
                            item_id = int(snap['item_id'])
                            qtd = snap['qtd']
                            deltas_por_item[item_id] = (
                                deltas_por_item.get(item_id, Decimal('0')) - qtd
                            )
                    continue

                item = cd.get('item')
                nova = cd.get('quantidade') or Decimal('0')
                if not item:
                    continue
                if nova <= 0:
                    messages.error(
                        request,
                        'Para remover um item, use Excluir na linha informativa ou ajuste pelo modal.',
                    )
                    erro_itens = True
                    break

                item_id = int(item.pk)
                if item_id in itens_ativos:
                    messages.error(
                        request,
                        'Não é permitido repetir o mesmo item em mais de uma linha.',
                    )
                    erro_itens = True
                    break

                itens_ativos.add(item_id)
                linhas_ativas += 1

                if inst.pk:
                    antes = existentes.get(inst.pk, {}).get('qtd', Decimal('0'))
                    delta = nova - antes
                else:
                    delta = nova
                deltas_por_item[item_id] = deltas_por_item.get(item_id, Decimal('0')) + delta

            if not erro_itens and linhas_ativas == 0:
                messages.error(
                    request,
                    'A requisição precisa ter ao menos 1 item. Para devolver tudo ao estoque, cancele a requisição.',
                )
                erro_itens = True

            if not erro_itens:
                try:
                    old_sol = req.solicitante_id
                    old_loc = req.local_id
                    old_obra = req.obra_id
                    with transaction.atomic():
                        for item_id, delta in deltas_por_item.items():
                            if delta == 0:
                                continue
                            locked = Item.objects.select_for_update().get(
                                pk=item_id, empresa=empresa, ativo=True
                            )
                            saldo_antes = locked.quantidade_estoque
                            if delta > 0 and delta > saldo_antes:
                                raise ValueError(
                                    f'saldo_insuficiente:{locked.descricao}:{delta}:{saldo_antes}'
                                )
                            locked.quantidade_estoque = saldo_antes - delta
                            locked.save(update_fields=['quantidade_estoque'])
                            registrar_auditoria(
                                request,
                                acao='update',
                                resumo=(
                                    f'Requisição #{req.pk}: ajuste estoque «{locked.descricao[:80]}» '
                                    f'(Δ {delta}). {saldo_antes} → {locked.quantidade_estoque}.'
                                ),
                                modulo='estoque',
                                detalhes={
                                    'requisicao_id': req.pk,
                                    'item_id': locked.pk,
                                    'item_descricao': locked.descricao[:120],
                                    'operacao': 'ajuste_por_edicao_requisicao',
                                    'delta': str(delta),
                                    'saldo_antes': str(saldo_antes),
                                    'saldo_depois': str(locked.quantidade_estoque),
                                },
                            )

                        form.save()
                        formset.save()

                    if (
                        req.solicitante_id != old_sol
                        or req.local_id != old_loc
                        or req.obra_id != old_obra
                    ):
                        registrar_auditoria(
                            request,
                            acao='update',
                            resumo=f'Requisição #{req.pk}: solicitante, local ou obra alterados.',
                            modulo='estoque',
                            detalhes={
                                'requisicao_id': req.pk,
                                'operacao': 'editar_cabecalho',
                                'solicitante_antes_id': old_sol,
                                'solicitante_depois_id': req.solicitante_id,
                                'local_antes_id': old_loc,
                                'local_depois_id': req.local_id,
                                'obra_antes_id': old_obra,
                                'obra_depois_id': req.obra_id,
                            },
                        )

                    messages.success(request, 'Requisição atualizada.')
                    detalhe_url = (
                        reverse_empresa(
                            request, 'estoque:detalhe_requisicao', kwargs={'pk': req.pk}
                        )
                        + '?'
                        + urlencode({'limpar_rascunho_edicao': '1'})
                    )
                    return redirect(detalhe_url)
                except ValueError as exc:
                    msg = str(exc)
                    if msg.startswith('saldo_insuficiente:'):
                        parts = msg.split(':', 3)
                        desc = parts[1] if len(parts) > 1 else 'item'
                        ped = parts[2] if len(parts) > 2 else ''
                        sal = parts[3] if len(parts) > 3 else ''
                        messages.error(
                            request,
                            f'Saldo insuficiente em "{desc}". Pedido adicional: {ped} · Saldo: {sal}.',
                        )
                    else:
                        messages.error(request, 'Não foi possível salvar a requisição.')

    else:
        form = RequisicaoEstoqueForm(instance=req, empresa=empresa)
        formset = RequisicaoEstoqueItemFormSetEdit(instance=req, prefix='itens')
        _bind_formset_empresa(formset, empresa)

    return render(
        request,
        'estoque/requisicoes/editar.html',
        {
            'page_title': f'Editar requisição #{req.pk}',
            'requisicao': req,
            'form': form,
            'formset': formset,
            'requisicao_draft_key': draft_key,
            'requisicao_clear_flag_key': clear_key,
            'devolver_item_url_base': reverse_empresa(
                request,
                'estoque:devolver_item_requisicao',
                kwargs={'pk': 0},
            ),
        },
    )


@login_required
def imprimir_requisicao(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    req = get_object_or_404(
        RequisicaoEstoque.objects.select_related(
            'solicitante__cargo', 'local', 'obra', 'almoxarife'
        ),
        pk=pk,
        empresa=empresa,
    )
    itens = list(
        req.itens.select_related('item', 'item__unidade_medida')
        .prefetch_related('item__imagens')
        .order_by('item__descricao')
    )
    return render(
        request,
        'estoque/requisicoes/imprimir.html',
        {
            'requisicao': req,
            'itens_requisicao': itens,
            'empresa': empresa,
        },
    )


@login_required
def imprimir_requisicao_pdf(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    req = get_object_or_404(
        RequisicaoEstoque.objects.select_related(
            'solicitante__cargo', 'local', 'obra', 'almoxarife'
        ),
        pk=pk,
        empresa=empresa,
    )
    itens = list(
        req.itens.select_related('item', 'item__unidade_medida')
        .prefetch_related('item__imagens')
        .order_by('item__descricao')
    )
    data = build_requisicao_pdf_bytes(empresa, req, itens)
    resp = HttpResponse(data, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="requisicao_{req.pk}.pdf"'
    return resp


@login_required
def cancelar_requisicao(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    req = get_object_or_404(
        RequisicaoEstoque.objects.prefetch_related('itens__item'),
        pk=pk,
        empresa=empresa,
    )

    if req.status != RequisicaoEstoque.Status.ATIVA:
        messages.info(request, 'Esta requisição já está cancelada.')
        return redirect_empresa(request, 'estoque:detalhe_requisicao', kwargs={'pk': req.pk})

    if request.method == 'POST':
        nome_req = f'#{req.pk}'
        with transaction.atomic():
            locked_req = RequisicaoEstoque.objects.select_for_update().get(
                pk=req.pk, empresa=empresa
            )
            if locked_req.status != RequisicaoEstoque.Status.ATIVA:
                messages.info(request, 'Esta requisição já estava cancelada.')
                return redirect_empresa(request, 'estoque:detalhe_requisicao', kwargs={'pk': req.pk})
            for ri in locked_req.itens.select_related('item'):
                locked = Item.objects.select_for_update().get(
                    pk=ri.item_id, empresa=empresa, ativo=True
                )
                qty = ri.quantidade or Decimal('0')
                if qty <= 0:
                    continue
                saldo_antes = locked.quantidade_estoque
                locked.quantidade_estoque = saldo_antes + qty
                locked.save(update_fields=['quantidade_estoque'])
                registrar_auditoria(
                    request,
                    acao='update',
                    resumo=(
                        f'Requisição {nome_req} cancelada: devolver {qty} de '
                        f'«{locked.descricao[:80]}» ({saldo_antes} → {locked.quantidade_estoque}).'
                    ),
                    modulo='estoque',
                    detalhes={
                        'requisicao_id': req.pk,
                        'requisicao_item_id': ri.pk,
                        'item_id': locked.pk,
                        'item_descricao': locked.descricao[:120],
                        'operacao': 'devolver_por_cancelamento_requisicao',
                        'quantidade': str(qty),
                        'saldo_antes': str(saldo_antes),
                        'saldo_depois': str(locked.quantidade_estoque),
                    },
                )
            locked_req.status = RequisicaoEstoque.Status.CANCELADA
            locked_req.save(update_fields=['status'])

        registrar_auditoria(
            request,
            acao='update',
            resumo=f'Requisição de estoque {nome_req} cancelada (estoque devolvido).',
            modulo='estoque',
            detalhes={
                'requisicao_id': req.pk,
                'operacao': 'cancelar_requisicao',
            },
        )
        messages.success(request, 'Requisição cancelada e estoque devolvido.')
        return redirect_empresa(request, 'estoque:requisicoes')

    return render(
        request,
        'estoque/requisicoes/confirmar_cancelamento_requisicao.html',
        {
            'page_title': 'Cancelar requisição',
            'requisicao': req,
        },
    )


@login_required
def nova_requisicao(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    almoxarife_label = (request.user.nome_completo or request.user.username)

    if request.method == 'POST':
        form = RequisicaoEstoqueForm(request.POST, empresa=empresa)
        formset = RequisicaoEstoqueItemFormSet(request.POST, prefix='itens')
        _bind_formset_empresa(formset, empresa)
        if form.is_valid():
            try:
                with transaction.atomic():
                    req = form.save(commit=False)
                    req.empresa = empresa
                    req.almoxarife = request.user
                    req.status = RequisicaoEstoque.Status.ATIVA
                    req.save()

                    formset = RequisicaoEstoqueItemFormSet(
                        request.POST,
                        instance=req,
                        prefix='itens',
                    )
                    _bind_formset_empresa(formset, empresa)
                    if not formset.is_valid():
                        messages.error(request, 'Revise os itens solicitados.')
                        raise ValueError('Itens inválidos')

                    itens_salvos = formset.save(commit=False)

                    movimentos = []
                    for ri in itens_salvos:
                        if not ri.item_id:
                            continue
                        qty = ri.quantidade or Decimal('0')
                        if qty <= 0:
                            continue
                        movimentos.append((ri.item_id, qty))

                    if not movimentos:
                        messages.error(request, 'Informe ao menos 1 item com quantidade.')
                        raise ValueError('Sem itens')

                    agg: dict[int, Decimal] = {}
                    for item_id, qty in movimentos:
                        agg[item_id] = agg.get(item_id, Decimal('0')) + qty

                    for item_id, qty in agg.items():
                        locked = Item.objects.select_for_update().get(
                            pk=item_id, empresa=empresa, ativo=True
                        )
                        saldo_antes = locked.quantidade_estoque
                        if qty > saldo_antes:
                            messages.error(
                                request,
                                f'Saldo insuficiente em "{locked.descricao}". '
                                f'Pedido: {qty} · Saldo: {saldo_antes}.',
                            )
                            raise ValueError('Saldo insuficiente')
                        locked.quantidade_estoque = saldo_antes - qty
                        locked.save(update_fields=['quantidade_estoque'])
                        registrar_auditoria(
                            request,
                            acao='update',
                            resumo=(
                                f'Requisição #{req.pk}: retirar {qty} de «{locked.descricao[:80]}» '
                                f'({saldo_antes} → {locked.quantidade_estoque}).'
                            ),
                            modulo='estoque',
                            detalhes={
                                'requisicao_id': req.pk,
                                'item_id': locked.pk,
                                'item_descricao': locked.descricao[:120],
                                'operacao': 'retirar',
                                'quantidade': str(qty),
                                'saldo_antes': str(saldo_antes),
                                'saldo_depois': str(locked.quantidade_estoque),
                            },
                        )

                    for ri in itens_salvos:
                        if ri.item_id and (ri.quantidade or 0) > 0:
                            ri.requisicao = req
                            ri.save()

                    for ri in formset.deleted_objects:
                        ri.delete()

                    registrar_auditoria(
                        request,
                        acao='create',
                        resumo=f'Requisição #{req.pk} cadastrada.',
                        modulo='estoque',
                        detalhes={
                            'requisicao_id': req.pk,
                            'operacao': 'criar_requisicao',
                        },
                    )

                messages.success(request, 'Requisição cadastrada e estoque movimentado.')
                lista_url = (
                    reverse_empresa(request, 'estoque:requisicoes')
                    + '?'
                    + urlencode({'limpar_rascunho_nova': '1'})
                )
                return redirect(lista_url)
            except ValueError:
                # Mensagens já foram adicionadas; rollback automático no atomic.
                # Re-bind do formset sem instance para re-renderizar a página com os mesmos índices do POST.
                formset = RequisicaoEstoqueItemFormSet(request.POST, prefix='itens')
                _bind_formset_empresa(formset, empresa)
        else:
            messages.error(request, 'Revise os campos e itens informados.')
    else:
        form = RequisicaoEstoqueForm(empresa=empresa)
        formset = RequisicaoEstoqueItemFormSet(prefix='itens')
        _bind_formset_empresa(formset, empresa)

    return render(
        request,
        'estoque/requisicoes/nova.html',
        {
            'page_title': 'Nova requisição',
            'form': form,
            'formset': formset,
            'almoxarife_label': almoxarife_label,
            'clear_draft_on_load': (request.method != 'POST' and (request.GET.get('fresh') or '').strip() == '1'),
        },
    )


@login_required
def autocomplete_solicitantes(request):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')
    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:nova_requisicao')
    q = (
        request.GET.get('q_solicitante_detail')
        or request.GET.get('q_solicitante')
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
def autocomplete_locais(request):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')
    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:nova_requisicao')
    q = (
        request.GET.get('q_local_detail')
        or request.GET.get('q_local')
        or request.GET.get('q')
        or ''
    ).strip()
    if len(q) < 2:
        return render(
            request,
            'estoque/requisicoes/_autocomplete_lista.html',
            {'items': [], 'hint': 'Digite pelo menos 2 caracteres.'},
        )
    items = list(Local.objects.filter(empresa=empresa, nome__icontains=q).order_by('nome')[:25])
    return render(
        request,
        'estoque/requisicoes/_autocomplete_lista.html',
        {'items': items, 'hint': ''},
    )


@login_required
def autocomplete_obras(request):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')
    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:nova_requisicao')
    q = (request.GET.get('q') or '').strip()
    if len(q) < 2:
        return render(
            request,
            'estoque/requisicoes/_autocomplete_lista.html',
            {'items': [], 'hint': 'Digite pelo menos 2 caracteres.'},
        )
    hoje = timezone.localdate()
    items = list(
        Obra.objects.filter(empresa=empresa, nome__icontains=q)
        .filter(Q(data_fim__isnull=True) | Q(data_fim__gte=hoje))
        .order_by('nome')[:25]
    )
    return render(
        request,
        'estoque/requisicoes/_autocomplete_lista.html',
        {'items': items, 'hint': ''},
    )


@login_required
def modal_buscar_itens_requisicao(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:nova_requisicao')

    return render(
        request,
        'estoque/partials/requisicao_buscar_itens_modal.html',
        {},
    )


@login_required
def partial_buscar_itens_requisicao(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:nova_requisicao')

    q = (request.GET.get('q') or '').strip()
    categoria_raw = (request.GET.get('categoria') or '').strip()

    # Ao abrir o modal: mostrar a tabela vazia (não listar tudo).
    if not q and not categoria_raw:
        return render(
            request,
            'estoque/requisicoes/_buscar_itens_lista.html',
            {
                'page_obj': [],
                'hint': 'Digite para buscar.',
            },
        )

    itens = (
        Item.objects.filter(empresa=empresa, ativo=True)
        .select_related('categoria', 'unidade_medida')
        .prefetch_related('imagens')
        .order_by('descricao')
    )
    if q:
        q_filter = Q(descricao__icontains=q) | Q(categoria__nome__icontains=q)
        if q.isdigit():
            q_filter |= Q(pk=int(q))
        itens = itens.filter(q_filter)
    if categoria_raw.isdigit():
        itens = itens.filter(categoria_id=int(categoria_raw))

    paginator = Paginator(itens, 20)
    page_param = request.GET.get('page') or 1
    try:
        page_obj = paginator.page(page_param)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(
        request,
        'estoque/requisicoes/_buscar_itens_lista.html',
        {
            'page_obj': page_obj,
            'hint': '',
        },
    )


@login_required
def modal_editar_item_requisicao(request, pk: int):
    """
    Modal para editar quantidade de um item já salvo na requisição.
    Também expõe a ação de devolver (excluir item + devolver ao estoque).
    """
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    if not _is_htmx(request):
        return _redirect_requisicao_contexto(request, 'estoque:requisicoes')

    ri = get_object_or_404(
        RequisicaoEstoqueItem.objects.select_related(
            'requisicao', 'item', 'item__categoria', 'item__unidade_medida'
        ),
        pk=pk,
        requisicao__empresa=empresa,
    )
    retorno_next = _next_path_requisicao(request)

    if ri.requisicao.status != RequisicaoEstoque.Status.ATIVA:
        return render(
            request,
            'estoque/requisicoes/partials/modal_item_editar.html',
            {
                'ri': ri,
                'requisicao_bloqueada': True,
                'retorno_next': retorno_next,
            },
            status=403,
        )

    if request.method == 'POST':
        raw = (request.POST.get('quantidade') or '').strip()
        try:
            nova = Decimal(str(raw).replace(',', '.'))
        except Exception:
            return render(
                request,
                'estoque/requisicoes/partials/modal_item_editar.html',
                {'ri': ri, 'erro': 'Quantidade inválida.', 'retorno_next': retorno_next},
                status=422,
            )
        if nova <= 0:
            return render(
                request,
                'estoque/requisicoes/partials/modal_item_editar.html',
                {
                    'ri': ri,
                    'erro': 'Informe uma quantidade maior que zero.',
                    'retorno_next': retorno_next,
                },
                status=422,
            )

        with transaction.atomic():
            locked_item = Item.objects.select_for_update().get(
                pk=ri.item_id, empresa=empresa, ativo=True
            )
            antes_req = ri.quantidade or Decimal('0')
            delta = nova - antes_req
            saldo_antes = locked_item.quantidade_estoque
            if delta > 0 and delta > saldo_antes:
                return render(
                    request,
                    'estoque/requisicoes/partials/modal_item_editar.html',
                    {
                        'ri': ri,
                        'erro': (
                            f'Saldo insuficiente. Pedido adicional: {delta} · '
                            f'Saldo: {saldo_antes}.'
                        ),
                        'retorno_next': retorno_next,
                    },
                    status=422,
                )
            # ajusta estoque conforme variação
            locked_item.quantidade_estoque = saldo_antes - delta
            locked_item.save(update_fields=['quantidade_estoque'])

            ri.quantidade = nova
            ri.save(update_fields=['quantidade'])

            registrar_auditoria(
                request,
                acao='update',
                resumo=(
                    f'Requisição #{ri.requisicao_id}: ajustar «{locked_item.descricao[:80]}» '
                    f'({antes_req} → {nova}). Estoque: {saldo_antes} → {locked_item.quantidade_estoque}.'
                ),
                modulo='estoque',
                detalhes={
                    'requisicao_id': ri.requisicao_id,
                    'requisicao_item_id': ri.pk,
                    'item_id': locked_item.pk,
                    'item_descricao': locked_item.descricao[:120],
                    'operacao': 'ajustar_quantidade',
                    'quantidade_antes': str(antes_req),
                    'quantidade_depois': str(nova),
                    'delta': str(delta),
                    'saldo_antes': str(saldo_antes),
                    'saldo_depois': str(locked_item.quantidade_estoque),
                },
            )

        # Recarrega relações para refletir estoque atualizado na UI
        ri = RequisicaoEstoqueItem.objects.select_related(
            'requisicao', 'item', 'item__categoria', 'item__unidade_medida'
        ).get(pk=ri.pk)
        messages.success(request, 'Item atualizado.')
        resp = render(
            request,
            'estoque/requisicoes/partials/modal_item_editar.html',
            {'ri': ri, 'retorno_next': retorno_next},
        )
        if retorno_next:
            return _htmx_redirect(resp, retorno_next)
        return resp

    return render(
        request,
        'estoque/requisicoes/partials/modal_item_editar.html',
        {'ri': ri, 'retorno_next': retorno_next},
    )


@login_required
def devolver_item_requisicao(request, pk: int):
    """
    Devolve quantidade ao estoque. Parcial: reduz a linha; total: remove a linha da requisição.
    POST quantidade_devolver opcional — se omitido, devolve o saldo total da linha.
    """
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    if request.method != 'POST':
        return _redirect_requisicao_contexto(request, 'estoque:requisicoes')
    if not _is_htmx(request) and not _wants_json(request):
        return _redirect_requisicao_contexto(request, 'estoque:requisicoes')

    ri = get_object_or_404(
        RequisicaoEstoqueItem.objects.select_related('requisicao', 'item'),
        pk=pk,
        requisicao__empresa=empresa,
    )
    retorno_next = _next_path_requisicao(request)
    wants_json = _wants_json(request)

    if ri.requisicao.status != RequisicaoEstoque.Status.ATIVA:
        if wants_json:
            return JsonResponse(
                {'ok': False, 'erro': 'Requisição cancelada: não é possível devolver itens pelo app.'},
                status=403,
            )
        return render(
            request,
            'estoque/requisicoes/partials/modal_item_editar.html',
            {
                'ri': ri,
                'requisicao_bloqueada': True,
                'retorno_next': retorno_next,
            },
            status=403,
        )

    def _erro(msg: str, status: int = 422):
        if wants_json:
            return JsonResponse({'ok': False, 'erro': msg}, status=status)
        return render(
            request,
            'estoque/requisicoes/partials/modal_item_editar.html',
            {'ri': ri, 'erro': msg, 'retorno_next': retorno_next},
            status=status,
        )

    antes = ri.quantidade or Decimal('0')
    if antes <= 0:
        return _erro('Linha sem quantidade para devolver.')

    raw_dev = (request.POST.get('quantidade_devolver') or '').strip()
    if raw_dev:
        try:
            qty_return = Decimal(str(raw_dev).replace(',', '.'))
        except Exception:
            return _erro('Quantidade a devolver inválida.')
    else:
        qty_return = antes

    if qty_return <= 0:
        return _erro('Informe uma quantidade maior que zero.')
    if qty_return > antes:
        return _erro(f'Não é possível devolver mais que o solicitado ({antes}).')

    is_total = qty_return >= antes

    with transaction.atomic():
        locked_item = Item.objects.select_for_update().get(
            pk=ri.item_id, empresa=empresa, ativo=True
        )
        requisicao_id = ri.requisicao_id
        saldo_antes = locked_item.quantidade_estoque
        locked_item.quantidade_estoque = saldo_antes + qty_return
        locked_item.save(update_fields=['quantidade_estoque'])

        if is_total:
            ri.delete()
            operacao = 'devolver_total'
            qtd_linha_depois = Decimal('0')
        else:
            ri.quantidade = antes - qty_return
            ri.save(update_fields=['quantidade'])
            operacao = 'devolver_parcial'
            qtd_linha_depois = ri.quantidade

        registrar_auditoria(
            request,
            acao='update',
            resumo=(
                f'Requisição #{requisicao_id}: devolver {qty_return} de «{locked_item.descricao[:80]}» '
                f'({saldo_antes} → {locked_item.quantidade_estoque}).'
                + (' Linha removida.' if is_total else f' Restante na requisição: {qtd_linha_depois}.')
            ),
            modulo='estoque',
            detalhes={
                'requisicao_id': requisicao_id,
                'requisicao_item_id': pk,
                'item_id': locked_item.pk,
                'item_descricao': locked_item.descricao[:120],
                'operacao': operacao,
                'quantidade_devolvida': str(qty_return),
                'quantidade_linha_antes': str(antes),
                'quantidade_linha_depois': str(qtd_linha_depois),
                'saldo_antes': str(saldo_antes),
                'saldo_depois': str(locked_item.quantidade_estoque),
            },
        )

    messages.success(
        request,
        'Devolução registrada e estoque atualizado.' if not is_total else 'Item devolvido ao estoque e removido da requisição.',
    )
    if wants_json:
        return JsonResponse(
            {
                'ok': True,
                'devolucao_total': is_total,
                'quantidade_devolvida': str(qty_return),
            }
        )
    resp = render(request, 'estoque/requisicoes/partials/modal_item_devolvido.html', {}, status=200)
    if retorno_next:
        return _htmx_redirect(resp, retorno_next)
    return resp

