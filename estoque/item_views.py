from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.db.models import F, Max, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.registry import registrar_auditoria

from core.urlutils import redirect_empresa, reverse_empresa

from .forms import ItemForm
from .models import CategoriaItem, Item, ItemImagem


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
            )
        else:
            form = ItemForm(request.POST, request.FILES, empresa=empresa)
        if form.is_valid():
            saved = form.save()
            _anexar_imagens_novas(saved, request.FILES.getlist('imagens'))
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
            form = ItemForm(instance=item, empresa=empresa)
        else:
            form = ItemForm(empresa=empresa)

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

    # Sem filtros na busca: só itens que precisam atenção (zerado ou abaixo do mín.).
    # Com qualquer filtro (texto, categoria ou situação): todos os itens ativos elegíveis.
    busca_expandida = bool(q) or categoria_raw.isdigit() or bool(situacao)

    itens = (
        Item.objects.filter(empresa=empresa, ativo=True)
        .select_related('categoria', 'unidade_medida')
        .prefetch_related('imagens')
        .order_by('descricao')
    )
    if not busca_expandida:
        itens = itens.filter(
            Q(quantidade_estoque=0)
            | Q(quantidade_estoque__lt=F('quantidade_minima'))
        )

    if q:
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

    categorias = CategoriaItem.objects.filter(empresa=empresa).order_by('nome')

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
