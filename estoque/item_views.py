from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.db.models import Case, Count, F, IntegerField, Max, Q, Value, When
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.registry import registrar_auditoria
from auditoria.models import RegistroAuditoria

from core.urlutils import redirect_empresa, reverse_empresa

from .forms import ItemForm
from .models import CategoriaItem, Item, ItemImagem, RequisicaoEstoque, RequisicaoEstoqueItem
from .qr_item import attach_auto_qrcode_to_item, parse_item_qr_payload

# Auditoria de requisição sem linha de item / sem alteração de saldo (evita linhas “em branco” no log).
_MOVIMENTAR_LOG_OPERACOES_EXCLUIDAS = frozenset(
    ('criar_requisicao', 'editar_cabecalho', 'cancelar_requisicao')
)


def _empresa(request):
    return getattr(request, 'empresa_ativa', None)


def _is_htmx(request):
    v = request.headers.get('HX-Request')
    if v is None:
        v = request.META.get('HTTP_HX_REQUEST')
    return str(v).lower() == 'true'


def _movimentar_page_url(request, page_num: int) -> str:
    base = reverse_empresa(request, 'estoque:movimentar_estoque')
    q = request.GET.copy()
    q.pop('partial', None)
    if page_num <= 1:
        q.pop('page', None)
    else:
        q['page'] = str(page_num)
    if q:
        return f'{base}?{q.urlencode()}'
    return base


def _movimentar_pagination_items(request, page_obj):
    """Lista de dicts: num (int|None), url (str|''), current (bool), ellipsis (bool)."""
    paginator = page_obj.paginator
    total = paginator.num_pages
    cur = page_obj.number
    if total <= 1:
        return []
    window = 2
    if total <= (window * 2 + 3):
        nums = list(range(1, total + 1))
    else:
        nums = [1]
        start = max(2, cur - window)
        end = min(total - 1, cur + window)
        if start > 2:
            nums.append(None)
        nums.extend(range(start, end + 1))
        if end < total - 1:
            nums.append(None)
        nums.append(total)
    items = []
    for n in nums:
        if n is None:
            items.append({'ellipsis': True, 'num': None, 'url': '', 'current': False})
        else:
            items.append(
                {
                    'ellipsis': False,
                    'num': n,
                    'url': _movimentar_page_url(request, n),
                    'current': n == cur,
                }
            )
    return items


def _parse_decimal_mov_log(val):
    if val is None or val == '':
        return None
    try:
        return Decimal(str(val))
    except InvalidOperation:
        return None


def _movimentar_log_resolve_requisicao_pk(d, req_existentes, item_para_req):
    """
    Retorna o pk de RequisicaoEstoque para montar URL de detalhe, ou None se
    a requisição não existir mais (ex.: excluída) e não houver fallback válido.
    """
    raw = d.get('requisicao_id')
    if raw is not None:
        try:
            rpk = int(raw)
            if rpk in req_existentes:
                return rpk
        except (TypeError, ValueError):
            pass
    riid = d.get('requisicao_item_id')
    if riid is not None:
        try:
            rpk = item_para_req.get(int(riid))
            if rpk is not None and rpk in req_existentes:
                return rpk
        except (TypeError, ValueError):
            pass
    return None


def _enriquecer_logs_movimentacao(request, empresa, logs_page_obj):
    """
    Anexa em cada RegistroAuditoria atributos usados em _movimentar_log.html
    (rótulo de item, quantidade, classificação da ação e URL da requisição).
    """
    if not logs_page_obj:
        return
    obj_list = getattr(logs_page_obj, 'object_list', None)
    if not obj_list:
        return

    item_ids = set()
    for log in obj_list:
        d = log.detalhes or {}
        if d.get('item_descricao'):
            continue
        raw_id = d.get('item_id')
        if raw_id is None:
            continue
        try:
            item_ids.add(int(raw_id))
        except (TypeError, ValueError):
            pass

    desc_por_item = {}
    if item_ids:
        for row in Item.objects.filter(
            pk__in=item_ids, empresa=empresa
        ).only('pk', 'descricao'):
            desc_por_item[row.pk] = row.descricao

    rids = set()
    ri_ids = set()
    for log in obj_list:
        d = log.detalhes or {}
        raw = d.get('requisicao_id')
        if raw is not None:
            try:
                rids.add(int(raw))
            except (TypeError, ValueError):
                pass
        raw_i = d.get('requisicao_item_id')
        if raw_i is not None:
            try:
                ri_ids.add(int(raw_i))
            except (TypeError, ValueError):
                pass

    item_para_req = {
        row['pk']: row['requisicao_id']
        for row in RequisicaoEstoqueItem.objects.filter(
            pk__in=ri_ids,
            requisicao__empresa=empresa,
        ).values('pk', 'requisicao_id')
    }
    req_from_items = set(item_para_req.values())
    candidatos_req = rids | req_from_items
    req_existentes = set(
        RequisicaoEstoque.objects.filter(
            empresa=empresa, pk__in=candidatos_req
        ).values_list('pk', flat=True)
    )

    for log in obj_list:
        d = log.detalhes or {}
        op = d.get('operacao') or ''

        desc = d.get('item_descricao')
        if not desc:
            raw_id = d.get('item_id')
            if raw_id is not None:
                try:
                    desc = desc_por_item.get(int(raw_id))
                except (TypeError, ValueError):
                    pass
        log.mov_item_label = desc or '—'

        delta = _parse_decimal_mov_log(d.get('delta'))

        qtd_disp = None
        if op not in ('criar_requisicao', 'editar_cabecalho'):
            qdv = d.get('quantidade_devolvida')
            if qdv not in (None, ''):
                qtd_disp = qdv
            elif d.get('quantidade') not in (None, ''):
                qtd_disp = d.get('quantidade')
            elif delta is not None and op in (
                'ajuste_por_edicao_requisicao',
                'ajustar_quantidade',
            ):
                if delta != 0:
                    qtd_disp = str(abs(delta))

        log.mov_qtd_label = qtd_disp if qtd_disp not in (None, '') else '—'

        saldo = d.get('saldo_depois')
        log.mov_saldo_label = saldo if saldo not in (None, '') else '—'

        rid = d.get('requisicao_id')
        req_pk_resolvido = _movimentar_log_resolve_requisicao_pk(
            d, req_existentes, item_para_req
        )
        req_url = None
        if req_pk_resolvido is not None:
            try:
                req_url = reverse_empresa(
                    request,
                    'estoque:detalhe_requisicao',
                    kwargs={'pk': req_pk_resolvido},
                )
            except (TypeError, ValueError):
                pass
        log.mov_req_url = req_url

        kind = 'outro'
        if op == 'adicionar' and rid is None:
            kind = 'manual_add'
        elif op == 'retirar' and rid is None:
            kind = 'manual_ret'
        elif rid is not None and op == 'retirar':
            kind = 'req_retirada'
        elif rid is not None and op in (
            'devolver_total',
            'devolver_parcial',
            'devolver_por_exclusao_requisicao',
            'devolver_por_cancelamento_requisicao',
        ):
            kind = 'req_devolucao'
        elif rid is not None and op in (
            'ajuste_por_edicao_requisicao',
            'ajustar_quantidade',
        ):
            if delta is not None and delta > 0:
                kind = 'req_retirada'
            elif delta is not None and delta < 0:
                kind = 'req_devolucao'
        elif rid is not None and op in (
            'criar_requisicao',
            'editar_cabecalho',
            'cancelar_requisicao',
        ):
            kind = 'req_meta'

        log.mov_acao_kind = kind


def _hx_redirect_lista(request, lista_viewname: str):
    resp = HttpResponse(status=200)
    resp['HX-Redirect'] = reverse_empresa(request, lista_viewname)
    return resp


def _anexar_imagens_novas(item, files_list):
    if not files_list:
        return
    agg = item.imagens.aggregate(m=Max('ordem'))
    nxt = (agg['m'] if agg['m'] is not None else -1) + 1
    for i, f in enumerate(files_list):
        ItemImagem.objects.create(item=item, imagem=f, ordem=nxt + i)


def _render_item_form_modal(request, item, form):
    if item is None:
        post_url = reverse_empresa(request, 'estoque:modal_novo_item')
        titulo_modal = 'Novo item'
        excluir_url = None
    else:
        post_url = reverse_empresa(
            request, 'estoque:modal_editar_item', kwargs={'pk': item.pk}
        )
        titulo_modal = f'Editar — {item.descricao[:80]}'
        excluir_url = reverse_empresa(
            request, 'estoque:modal_excluir_item', kwargs={'pk': item.pk}
        )
    return render(
        request,
        'estoque/partials/item_form_modal.html',
        {
            'form': form,
            'post_url': post_url,
            'titulo_modal': titulo_modal,
            'item': item,
            'excluir_url': excluir_url,
        },
    )


def _modal_item_form(request, item):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:lista_itens')

    if item is not None:
        item = get_object_or_404(
            Item.objects.prefetch_related('imagens'),
            pk=item.pk,
            empresa=empresa,
        )

    if request.method == 'POST':
        if item is not None:
            form = ItemForm(
                request.POST,
                request.FILES,
                instance=item,
                empresa=empresa,
                lock_quantidade_estoque=True,
                lock_qrcode_imagem=True,
            )
        else:
            form = ItemForm(
                request.POST,
                request.FILES,
                empresa=empresa,
                lock_quantidade_estoque=True,
                lock_qrcode_imagem=True,
            )
        if form.is_valid():
            saved = form.save()
            _anexar_imagens_novas(saved, request.FILES.getlist('imagens'))
            attach_auto_qrcode_to_item(saved)
            if item is None:
                registrar_auditoria(
                    request,
                    acao='create',
                    resumo=f'Item «{saved.descricao[:80]}» cadastrado.',
                    modulo='estoque',
                    detalhes={'item_id': saved.pk},
                )
                messages.success(request, 'Item cadastrado.')
            else:
                registrar_auditoria(
                    request,
                    acao='update',
                    resumo=f'Item «{saved.descricao[:80]}» atualizado.',
                    modulo='estoque',
                    detalhes={'item_id': saved.pk},
                )
                messages.success(request, 'Item atualizado.')
            return _hx_redirect_lista(request, 'estoque:lista_itens')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        if item is not None:
            form = ItemForm(
                instance=item,
                empresa=empresa,
                lock_quantidade_estoque=True,
                lock_qrcode_imagem=True,
            )
        else:
            form = ItemForm(
                empresa=empresa,
                lock_quantidade_estoque=True,
                lock_qrcode_imagem=True,
            )
        preselect_categoria = (request.GET.get('preselect_categoria') or '').strip()
        if preselect_categoria.isdigit() and 'categoria' in form.fields:
            form.fields['categoria'].initial = int(preselect_categoria)

    return _render_item_form_modal(request, item, form)


@login_required
def lista_itens(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    q = (request.GET.get('q') or '').strip()
    itens = (
        Item.objects.filter(empresa=empresa)
        .select_related('categoria', 'unidade_medida', 'fornecedor')
        .prefetch_related('imagens')
        .order_by('descricao')
    )
    if q:
        itens = itens.filter(
            Q(descricao__icontains=q)
            | Q(marca__icontains=q)
            | Q(categoria__nome__icontains=q)
        )
    ctx = {
        'page_title': 'Itens',
        'itens': itens,
        'q': q,
    }
    if _is_htmx(request):
        return render(request, 'estoque/itens/_lista_conteudo.html', ctx)
    return render(request, 'estoque/itens/lista.html', ctx)


TODO_ESTOQUE_ITENS_POR_PAGINA = 20

TODO_ESTOQUE_SORT_COLUMNS = frozenset(
    {
        'descricao',
        'categoria',
        'unidade',
        'peso',
        'preco',
        'saldo',
        'minimo',
        'situacao',
    }
)


def _todo_estoque_sort_url(request, column: str) -> str:
    """Alterna asc/desc se a coluna já for a ativa; reseta página para 1."""
    base = reverse_empresa(request, 'estoque:todo_estoque')
    qp = request.GET.copy()
    qp.pop('partial', None)
    cur_o = (qp.get('ordem') or 'descricao').strip()
    cur_d = (qp.get('dir') or 'asc').strip().lower()
    if cur_d not in ('asc', 'desc'):
        cur_d = 'asc'
    if cur_o not in TODO_ESTOQUE_SORT_COLUMNS:
        cur_o = 'descricao'
    if column == cur_o:
        new_d = 'desc' if cur_d == 'asc' else 'asc'
    else:
        new_d = 'asc'
    qp['ordem'] = column
    qp['dir'] = new_d
    qp.pop('page', None)
    if qp:
        return f'{base}?{qp.urlencode()}'
    return base


def _todo_estoque_apply_order(itens, ordem: str, dir_: str):
    """Aplica ordenação estável (desempate por descrição)."""
    desc = dir_ == 'desc'
    if ordem == 'situacao':
        itens = itens.annotate(
            _ord_situacao=Case(
                When(quantidade_estoque__lte=0, then=Value(0)),
                When(
                    quantidade_minima__gt=0,
                    quantidade_estoque__lt=F('quantidade_minima'),
                    then=Value(1),
                ),
                When(
                    quantidade_minima__gt=0,
                    quantidade_estoque=F('quantidade_minima'),
                    then=Value(2),
                ),
                default=Value(3),
                output_field=IntegerField(),
            )
        )
        primary = (
            F('_ord_situacao').desc(nulls_last=True)
            if desc
            else F('_ord_situacao').asc(nulls_last=True)
        )
        return itens.order_by(primary, 'descricao')
    if ordem == 'categoria':
        primary = (
            F('categoria__nome').desc(nulls_last=True)
            if desc
            else F('categoria__nome').asc(nulls_last=True)
        )
        return itens.order_by(primary, 'descricao')
    if ordem == 'unidade':
        primary = (
            F('unidade_medida__abreviada').desc(nulls_last=True)
            if desc
            else F('unidade_medida__abreviada').asc(nulls_last=True)
        )
        return itens.order_by(primary, 'descricao')
    if ordem == 'peso':
        primary = F('peso').desc(nulls_last=True) if desc else F('peso').asc(nulls_last=True)
        return itens.order_by(primary, 'descricao')
    if ordem == 'preco':
        primary = F('preco').desc(nulls_last=True) if desc else F('preco').asc(nulls_last=True)
        return itens.order_by(primary, 'descricao')
    if ordem == 'saldo':
        primary = (
            F('quantidade_estoque').desc(nulls_last=True)
            if desc
            else F('quantidade_estoque').asc(nulls_last=True)
        )
        return itens.order_by(primary, 'descricao')
    if ordem == 'minimo':
        primary = (
            F('quantidade_minima').desc(nulls_last=True)
            if desc
            else F('quantidade_minima').asc(nulls_last=True)
        )
        return itens.order_by(primary, 'descricao')
    # descricao (default)
    primary = F('descricao').desc(nulls_last=True) if desc else F('descricao').asc(nulls_last=True)
    return itens.order_by(primary, 'descricao')


def _todo_estoque_page_url(request, page_num: int) -> str:
    base = reverse_empresa(request, 'estoque:todo_estoque')
    q = request.GET.copy()
    q.pop('partial', None)
    if page_num <= 1:
        q.pop('page', None)
    else:
        q['page'] = str(page_num)
    if q:
        return f'{base}?{q.urlencode()}'
    return base


def _todo_estoque_pagination_items(request, page_obj):
    """Mesmo padrão de _movimentar_pagination_items, para a página Todo o estoque."""
    paginator = page_obj.paginator
    total = paginator.num_pages
    cur = page_obj.number
    if total <= 1:
        return []
    window = 2
    if total <= (window * 2 + 3):
        nums = list(range(1, total + 1))
    else:
        nums = [1]
        start = max(2, cur - window)
        end = min(total - 1, cur + window)
        if start > 2:
            nums.append(None)
        nums.extend(range(start, end + 1))
        if end < total - 1:
            nums.append(None)
        nums.append(total)
    items = []
    for n in nums:
        if n is None:
            items.append({'ellipsis': True, 'num': None, 'url': '', 'current': False})
        else:
            items.append(
                {
                    'ellipsis': False,
                    'num': n,
                    'url': _todo_estoque_page_url(request, n),
                    'current': n == cur,
                }
            )
    return items


@login_required
def todo_estoque(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    # Pedido HTMX: só resultados. Link copiado sem HTMX deve renderizar a página completa.
    if request.GET.get('partial') == 'todo' and not _is_htmx(request):
        qp = request.GET.copy()
        qp.pop('partial', None)
        base = reverse_empresa(request, 'estoque:todo_estoque')
        if qp:
            return redirect(f'{base}?{qp.urlencode()}')
        return redirect(base)

    q = (request.GET.get('q') or '').strip()
    categoria_raw = (request.GET.get('categoria') or '').strip()
    situacao = (request.GET.get('situacao') or '').strip()
    ordem_raw = (request.GET.get('ordem') or 'descricao').strip()
    dir_raw = (request.GET.get('dir') or 'asc').strip().lower()
    if dir_raw not in ('asc', 'desc'):
        dir_raw = 'asc'
    if ordem_raw not in TODO_ESTOQUE_SORT_COLUMNS:
        ordem_raw = 'descricao'

    listar_todos = q.lower() == '#todos'

    itens = (
        Item.objects.filter(empresa=empresa, ativo=True)
        .select_related('categoria', 'unidade_medida')
        .prefetch_related('imagens')
    )

    if q and not listar_todos:
        itens = itens.filter(
            Q(descricao__icontains=q)
            | Q(marca__icontains=q)
            | Q(categoria__nome__icontains=q)
        )

    if categoria_raw.isdigit():
        itens = itens.filter(categoria_id=int(categoria_raw))

    if situacao == 'atencao':
        itens = itens.filter(
            Q(quantidade_estoque=0) | Q(quantidade_estoque__lt=F('quantidade_minima'))
        )
    elif situacao == 'zerado':
        itens = itens.filter(quantidade_estoque__lte=0)
    elif situacao == 'abaixo_min':
        itens = itens.filter(
            quantidade_estoque__gt=0,
            quantidade_minima__gt=0,
            quantidade_estoque__lt=F('quantidade_minima'),
        )

    itens = _todo_estoque_apply_order(itens, ordem_raw, dir_raw)

    categorias = CategoriaItem.objects.filter(empresa=empresa).order_by('nome')

    # Resumo por categoria (itens ativos).
    resumo_por_categoria = list(
        CategoriaItem.objects.filter(empresa=empresa)
        .annotate(
            qtd_itens=Count(
                'itens',
                filter=Q(itens__empresa=empresa, itens__ativo=True),
            )
        )
        .order_by('-qtd_itens', 'nome')
    )

    paginator = Paginator(itens, TODO_ESTOQUE_ITENS_POR_PAGINA)
    page_param = request.GET.get('page') or 1
    try:
        page_obj = paginator.page(page_param)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    ctx = {
        'page_title': 'Todo o estoque',
        'todo_itens_por_pagina': TODO_ESTOQUE_ITENS_POR_PAGINA,
        'todo_ordem': ordem_raw,
        'todo_dir': dir_raw,
        'todo_sort': {col: _todo_estoque_sort_url(request, col) for col in sorted(TODO_ESTOQUE_SORT_COLUMNS)},
        'page_obj': page_obj,
        'q': q,
        'categoria_filtro': categoria_raw if categoria_raw.isdigit() else '',
        'situacao_filtro': situacao,
        'categorias': categorias,
        'todo_url_prev': (
            _todo_estoque_page_url(request, page_obj.previous_page_number())
            if page_obj.has_previous()
            else None
        ),
        'todo_url_next': (
            _todo_estoque_page_url(request, page_obj.next_page_number())
            if page_obj.has_next()
            else None
        ),
        'todo_pagination_items': _todo_estoque_pagination_items(request, page_obj),
        'resumo_por_categoria': resumo_por_categoria,
    }
    if _is_htmx(request) or request.GET.get('partial') == 'todo':
        return render(request, 'estoque/_todo_estoque_resultados.html', ctx)
    return render(request, 'estoque/todo_estoque.html', ctx)


@login_required
def movimentar_estoque(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    # Pedido vindo do formulário HTMX inclui partial=movimentar; visita direta à URL copiada
    # não deve mostrar só o fragmento — redireciona sem o parâmetro.
    if request.GET.get('partial') == 'movimentar' and not _is_htmx(request):
        qp = request.GET.copy()
        qp.pop('partial', None)
        base = reverse_empresa(request, 'estoque:movimentar_estoque')
        if qp:
            return redirect(f'{base}?{qp.urlencode()}')
        return redirect(base)

    q = (request.GET.get('q') or '').strip()
    categoria_raw = (request.GET.get('categoria') or '').strip()
    situacao = (request.GET.get('situacao') or '').strip()
    listar_todos = q.lower() == '#todos'

    # Sem filtros: lista vazia (use a busca). Com texto, categoria ou situação: itens ativos filtrados.
    # Busca exata "#todos" lista todos os itens ativos da empresa (ainda respeita categoria/situação).
    busca_expandida = bool(q) or categoria_raw.isdigit() or bool(situacao)

    itens = (
        Item.objects.filter(empresa=empresa, ativo=True)
        .select_related('categoria', 'unidade_medida')
        .prefetch_related('imagens')
        .order_by('descricao')
    )
    if not busca_expandida:
        itens = itens.none()

    if q and not listar_todos:
        itens = itens.filter(
            Q(descricao__icontains=q)
            | Q(marca__icontains=q)
            | Q(categoria__nome__icontains=q)
        )

    if categoria_raw.isdigit():
        itens = itens.filter(categoria_id=int(categoria_raw))

    if situacao == 'zerado':
        itens = itens.filter(quantidade_estoque__lte=0)
    elif situacao == 'abaixo_min':
        itens = itens.filter(
            quantidade_estoque__gt=0,
            quantidade_minima__gt=0,
            quantidade_estoque__lt=F('quantidade_minima'),
        )
    elif situacao == 'atencao':
        itens = itens.filter(
            Q(quantidade_estoque=0)
            | Q(quantidade_estoque__lt=F('quantidade_minima'))
        )

    categorias = CategoriaItem.objects.filter(empresa=empresa).order_by('nome')

    log_busca = (request.GET.get('log_q') or '').strip()

    logs_qs = (
        RegistroAuditoria.objects.filter(
            empresa=empresa,
            modulo='estoque',
            detalhes__has_key='operacao',
        )
        .exclude(detalhes__operacao__in=_MOVIMENTAR_LOG_OPERACOES_EXCLUIDAS)
        .select_related('usuario')
        .only('criado_em', 'usuario__username', 'usuario__nome_completo', 'detalhes', 'resumo')
        .order_by('-criado_em')
    )
    if log_busca:
        # Inclui movimentos onde só há item_id no JSON (legado) ou descrição diferente do texto atual.
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
    logs_paginator = Paginator(logs_qs, 20)
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
    log_query = log_q.urlencode()

    paginator = Paginator(itens, 20)
    page_param = request.GET.get('page') or 1
    try:
        page_obj = paginator.page(page_param)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    ctx = {
        'page_title': 'Movimentar estoque',
        'page_obj': page_obj,
        'q': q,
        'categoria_filtro': categoria_raw if categoria_raw.isdigit() else '',
        'situacao_filtro': situacao,
        'movimentar_busca_expandida': busca_expandida,
        'categorias': categorias,
        'movimentar_url_prev': (
            _movimentar_page_url(request, page_obj.previous_page_number())
            if page_obj.has_previous()
            else None
        ),
        'movimentar_url_next': (
            _movimentar_page_url(request, page_obj.next_page_number())
            if page_obj.has_next()
            else None
        ),
        'movimentar_pagination_items': _movimentar_pagination_items(request, page_obj),
        'logs_page_obj': logs_page_obj,
        'log_query': log_query,
        'log_busca': log_busca,
    }
    if _is_htmx(request) or request.GET.get('partial') == 'movimentar':
        return render(request, 'estoque/itens/_movimentar_conteudo.html', ctx)
    return render(request, 'estoque/itens/movimentar.html', ctx)


def _render_movimentar_saldo_modal(
    request,
    item,
    *,
    errors=(),
    operacao='retirar',
    quantidade_val='',
):
    post_url = reverse_empresa(
        request, 'estoque:modal_movimentar_saldo', kwargs={'pk': item.pk}
    )
    return render(
        request,
        'estoque/partials/movimentar_saldo_modal.html',
        {
            'item': item,
            'post_url': post_url,
            'errors': errors,
            'operacao': operacao if operacao in ('adicionar', 'retirar') else 'retirar',
            'quantidade_val': quantidade_val,
        },
    )


@login_required
def modal_movimentar_saldo(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item = get_object_or_404(
        Item.objects.select_related('unidade_medida'),
        pk=pk,
        empresa=empresa,
        ativo=True,
    )

    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:movimentar_estoque')

    if request.method == 'POST':
        operacao = (request.POST.get('operacao') or '').strip()
        qty_raw = (request.POST.get('quantidade') or '').strip().replace(',', '.')
        errors = []

        if operacao not in ('adicionar', 'retirar'):
            errors.append('Operação inválida.')

        qty = None
        if not qty_raw:
            errors.append('Informe a quantidade.')
        else:
            try:
                qty = Decimal(qty_raw)
            except InvalidOperation:
                errors.append('Quantidade inválida.')
                qty = None

        if qty is not None:
            if qty <= 0:
                errors.append('Informe uma quantidade maior que zero.')
            else:
                exp = qty.as_tuple().exponent
                if isinstance(exp, int) and exp < -4:
                    errors.append('Use no máximo 4 casas decimais.')

        if not errors and qty is not None:
            with transaction.atomic():
                locked = Item.objects.select_for_update().get(
                    pk=item.pk, empresa=empresa, ativo=True
                )
                saldo_antes = locked.quantidade_estoque
                if operacao == 'retirar':
                    if qty > saldo_antes:
                        errors.append(
                            'Não é possível retirar mais do que o saldo atual.'
                        )
                    else:
                        locked.quantidade_estoque = saldo_antes - qty
                else:
                    locked.quantidade_estoque = saldo_antes + qty

                if not errors:
                    try:
                        locked.full_clean()
                    except ValidationError as exc:
                        if exc.error_dict:
                            for msgs in exc.error_dict.values():
                                errors.extend(str(m) for m in msgs)
                        else:
                            errors.extend(str(m) for m in exc.error_list)
                        if not errors:
                            errors.append('Não foi possível salvar o saldo.')

                if not errors:
                    locked.save(update_fields=['quantidade_estoque'])
                    saldo_depois = locked.quantidade_estoque
                    registrar_auditoria(
                        request,
                        acao='update',
                        resumo=(
                            f'Estoque «{locked.descricao[:80]}»: '
                            f'{operacao} {qty} ({saldo_antes} → {saldo_depois}).'
                        ),
                        modulo='estoque',
                        detalhes={
                            'item_id': locked.pk,
                            'item_descricao': locked.descricao[:120],
                            'operacao': operacao,
                            'quantidade': str(qty),
                            'saldo_antes': str(saldo_antes),
                            'saldo_depois': str(saldo_depois),
                        },
                    )
                    messages.success(request, 'Estoque atualizado.')
                    resp = HttpResponse(status=200)
                    resp['HX-Redirect'] = (
                        request.headers.get('HX-Current-URL')
                        or reverse_empresa(request, 'estoque:movimentar_estoque')
                    )
                    return resp

        return _render_movimentar_saldo_modal(
            request,
            item,
            errors=errors,
            operacao=operacao,
            quantidade_val=request.POST.get('quantidade') or '',
        )

    return _render_movimentar_saldo_modal(request, item)


@login_required
def modal_novo_item(request):
    return _modal_item_form(request, None)


@login_required
def modal_editar_item(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    item = get_object_or_404(Item, pk=pk, empresa=empresa)
    return _modal_item_form(request, item)


@login_required
def modal_gerar_qrcode_item(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item = get_object_or_404(
        Item.objects.prefetch_related('imagens'),
        pk=pk,
        empresa=empresa,
    )

    if request.method != 'POST':
        return redirect_empresa(request, 'estoque:lista_itens')

    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:lista_itens')

    if item.qrcode_imagem:
        messages.info(request, 'Este item já possui QR Code.')
    else:
        from django.conf import settings

        ok, err = attach_auto_qrcode_to_item(item)
        item.refresh_from_db()
        if ok and item.qrcode_imagem:
            messages.success(request, 'QR Code gerado.')
        else:
            msg = 'Não foi possível gerar o QR Code. Tente de novo.'
            if settings.DEBUG and err:
                msg = f'{msg} ({err})'
            messages.warning(request, msg)

    form = ItemForm(
        instance=item,
        empresa=empresa,
        lock_quantidade_estoque=True,
        lock_qrcode_imagem=True,
    )
    return _render_item_form_modal(request, item, form)


@login_required
def modal_excluir_qrcode_item(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item = get_object_or_404(
        Item.objects.prefetch_related('imagens'),
        pk=pk,
        empresa=empresa,
    )

    if request.method != 'POST':
        return redirect_empresa(request, 'estoque:lista_itens')

    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:lista_itens')

    if item.qrcode_imagem:
        item.qrcode_imagem.delete(save=False)
        item.save(update_fields=['qrcode_imagem'])
        messages.success(
            request,
            'QR Code removido. Use «Gerar QR Code» para criar outro.',
        )
    else:
        messages.info(request, 'Este item não tinha QR Code.')

    item.refresh_from_db()
    form = ItemForm(
        instance=item,
        empresa=empresa,
        lock_quantidade_estoque=True,
        lock_qrcode_imagem=True,
    )
    return _render_item_form_modal(request, item, form)


@login_required
def modal_excluir_item(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item = get_object_or_404(Item, pk=pk, empresa=empresa)
    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:item_excluir', kwargs={'pk': pk})

    return render(
        request,
        'estoque/partials/item_excluir_modal.html',
        {
            'item': item,
            'excluir_url': reverse_empresa(
                request, 'estoque:item_excluir', kwargs={'pk': pk}
            ),
            'voltar_editar_url': reverse_empresa(
                request, 'estoque:modal_editar_item', kwargs={'pk': pk}
            ),
        },
    )


@login_required
def leitor_estoque_resolve(request):
    """Resolve texto lido pelo leitor 2D (QR) para um item da empresa ativa."""
    empresa = _empresa(request)
    if not empresa:
        return JsonResponse({'ok': False, 'error': 'empresa'}, status=400)
    parsed = parse_item_qr_payload(request.GET.get('c') or '')
    if not parsed:
        return JsonResponse({'ok': False, 'error': 'invalid'}, status=400)
    eid, iid = parsed
    if eid != empresa.pk:
        return JsonResponse({'ok': False, 'error': 'empresa'}, status=403)
    if not Item.objects.filter(pk=iid, empresa_id=empresa.pk).exists():
        return JsonResponse({'ok': False, 'error': 'not_found'}, status=404)
    return JsonResponse({'ok': True, 'item_id': iid})


@login_required
def item_novo(request):
    return redirect_empresa(request, 'estoque:lista_itens')


@login_required
def item_editar(request, pk):
    return redirect_empresa(request, 'estoque:lista_itens')


@login_required
def item_imagem_excluir(request, item_pk, imagem_pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item = get_object_or_404(Item, pk=item_pk, empresa=empresa)
    img = get_object_or_404(ItemImagem, pk=imagem_pk, item=item)
    if request.method == 'POST':
        img.imagem.delete(save=False)
        img.delete()
        messages.success(request, 'Imagem removida.')
        item = get_object_or_404(
            Item.objects.prefetch_related('imagens'),
            pk=item_pk,
            empresa=empresa,
        )
        form = ItemForm(instance=item, empresa=empresa)
        if _is_htmx(request):
            return _render_item_form_modal(request, item, form)
        return redirect_empresa(request, 'estoque:item_editar', pk=item.pk)

    return redirect_empresa(request, 'estoque:item_editar', pk=item.pk)


@login_required
def item_excluir(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item = get_object_or_404(Item, pk=pk, empresa=empresa)
    if request.method == 'POST':
        desc = item.descricao[:120]
        iid = item.pk
        for img in list(item.imagens.all()):
            img.imagem.delete(save=False)
            img.delete()
        if item.qrcode_imagem:
            item.qrcode_imagem.delete(save=False)
        item.delete()
        registrar_auditoria(
            request,
            acao='delete',
            resumo=f'Item «{desc}» excluído.',
            modulo='estoque',
            detalhes={'item_id': iid},
        )
        messages.success(request, 'Item excluído.')
        if _is_htmx(request):
            return _hx_redirect_lista(request, 'estoque:lista_itens')
        return redirect_empresa(request, 'estoque:lista_itens')

    return render(
        request,
        'estoque/itens/excluir.html',
        {
            'page_title': 'Excluir item',
            'item': item,
        },
    )
