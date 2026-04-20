from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from auditoria.registry import registrar_auditoria

from core.urlutils import redirect_empresa, reverse_empresa

from .item_views import _empresa
from .lista_compra_forms import (
    ListaCompraEstoqueForm,
    ListaCompraEstoqueItemFormSetEdit,
    ListaCompraEstoqueItemFormSetNova,
)
from .models import Item, ListaCompraEstoque


def _is_htmx(request) -> bool:
    v = request.headers.get('HX-Request')
    if v is None:
        v = request.META.get('HTTP_HX_REQUEST')
    return str(v).lower() == 'true'


def _hx_redirect_lista(request) -> HttpResponse:
    resp = HttpResponse(status=200)
    resp['HX-Redirect'] = reverse_empresa(
        request, 'estoque:lista_compra_estoque'
    )
    return resp


def _item_queryset_para_lista(empresa, lista: ListaCompraEstoque | None):
    qs = Item.objects.filter(empresa=empresa).select_related(
        'unidade_medida'
    ).order_by('descricao')
    if lista and lista.pk:
        used = list(lista.itens.values_list('item_id', flat=True))
        return qs.filter(Q(ativo=True) | Q(pk__in=used)).distinct()
    return qs.filter(ativo=True)


def _bind_lista_compra_formset(formset, empresa, lista: ListaCompraEstoque | None):
    item_qs = _item_queryset_para_lista(empresa, lista)
    for f in formset.forms:
        if 'item' in f.fields:
            f.fields['item'].queryset = item_qs
    if hasattr(formset, 'empty_form') and 'item' in formset.empty_form.fields:
        formset.empty_form.fields['item'].queryset = item_qs


def _lista_formset_row_pairs(formset, empresa):
    """Par (form, Item|None) alinhado a cada linha do formset para o template/JS."""
    raw_data = getattr(formset, 'data', None)
    ids: list[int] = []
    for f in formset.forms:
        inst = getattr(f, 'instance', None)
        if inst and inst.pk and inst.item_id:
            ids.append(inst.item_id)
        if raw_data is not None:
            v = raw_data.get(f.add_prefix('item'))
            if v and str(v).isdigit():
                ids.append(int(v))
    item_map: dict[int, Item] = {}
    if ids:
        item_map = {
            i.pk: i
            for i in Item.objects.filter(pk__in=set(ids), empresa=empresa)
            .select_related('categoria', 'unidade_medida', 'fornecedor')
            .prefetch_related('imagens')
        }
    pairs = []
    for f in formset.forms:
        item = None
        inst = getattr(f, 'instance', None)
        if inst and inst.pk and inst.item_id:
            item = inst.item
        elif raw_data is not None:
            v = raw_data.get(f.add_prefix('item'))
            if v and str(v).isdigit():
                item = item_map.get(int(v))
        pairs.append((f, item))
    return pairs


def _ctx_lista_compra_form(
    form,
    formset,
    empresa,
    modo: str,
    lista: ListaCompraEstoque | None,
    page_title: str,
):
    _bind_lista_compra_formset(formset, empresa, lista)
    rows = _lista_formset_row_pairs(formset, empresa)
    return {
        'page_title': page_title,
        'form': form,
        'formset': formset,
        'modo': modo,
        'lista': lista,
        'lista_formset_rows': rows,
        'lc_server_hydrate': len(rows) > 0,
    }


@login_required
def lista_compra_estoque(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    q = (request.GET.get('q') or '').strip()
    status_f = (request.GET.get('status') or '').strip()
    valid_status = {c[0] for c in ListaCompraEstoque.Status.choices}
    if status_f not in valid_status:
        status_f = ''

    qs = (
        ListaCompraEstoque.objects.filter(empresa=empresa)
        .annotate(n_itens=Count('itens', distinct=True))
        .order_by('-data_pedido', '-pk')
    )
    if status_f:
        qs = qs.filter(status=status_f)
    if q:
        qs = qs.filter(
            Q(nome__icontains=q)
            | Q(observacoes__icontains=q)
            | Q(itens__item__descricao__icontains=q)
            | Q(itens__item__marca__icontains=q)
        ).distinct()

    ctx = {
        'page_title': 'Listas de compra',
        'listas': qs,
        'q': q,
        'status_f': status_f,
        'status_choices': ListaCompraEstoque.Status.choices,
    }
    if _is_htmx(request):
        return render(request, 'estoque/lista_compra/_lista_conteudo.html', ctx)
    return render(request, 'estoque/lista_compra/lista.html', ctx)


@login_required
def nova_lista_compra_estoque(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    FormSet = ListaCompraEstoqueItemFormSetNova
    if request.method == 'POST':
        form = ListaCompraEstoqueForm(request.POST)
        formset = FormSet(request.POST, prefix='itens')
        _bind_lista_compra_formset(formset, empresa, None)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                lista = form.save(commit=False)
                lista.empresa = empresa
                lista.criado_por = request.user
                lista.save()
                formset.instance = lista
                formset.save()
            registrar_auditoria(
                request,
                acao='create',
                resumo=f'Lista de compra #{lista.pk} registrada ({lista.get_status_display()}).',
                modulo='estoque',
                detalhes={'lista_compra_id': lista.pk},
            )
            messages.success(request, 'Lista de compra criada.')
            return redirect_empresa(request, 'estoque:lista_compra_estoque')
        messages.error(request, 'Corrija os campos destacados.')
    else:
        form = ListaCompraEstoqueForm(
            initial={'data_pedido': timezone.localdate()}
        )
        formset = FormSet(prefix='itens')
        _bind_lista_compra_formset(formset, empresa, None)

    ctx = _ctx_lista_compra_form(
        form,
        formset,
        empresa,
        'nova',
        None,
        'Nova lista de compra',
    )
    return render(request, 'estoque/lista_compra/form.html', ctx)


@login_required
def editar_lista_compra_estoque(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    lista = get_object_or_404(
        ListaCompraEstoque.objects.prefetch_related(
            'itens__item__categoria',
            'itens__item__unidade_medida',
            'itens__item__fornecedor',
            'itens__item__imagens',
        ),
        pk=pk,
        empresa=empresa,
    )
    FormSet = ListaCompraEstoqueItemFormSetEdit

    if request.method == 'POST':
        form = ListaCompraEstoqueForm(request.POST, instance=lista)
        formset = FormSet(request.POST, instance=lista, prefix='itens')
        _bind_lista_compra_formset(formset, empresa, lista)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
            registrar_auditoria(
                request,
                acao='update',
                resumo=f'Lista de compra #{lista.pk} atualizada.',
                modulo='estoque',
                detalhes={'lista_compra_id': lista.pk},
            )
            messages.success(request, 'Lista de compra atualizada.')
            return redirect_empresa(request, 'estoque:lista_compra_estoque')
        messages.error(request, 'Corrija os campos destacados.')
    else:
        form = ListaCompraEstoqueForm(instance=lista)
        formset = FormSet(instance=lista, prefix='itens')
        _bind_lista_compra_formset(formset, empresa, lista)

    ctx = _ctx_lista_compra_form(
        form,
        formset,
        empresa,
        'editar',
        lista,
        f'Lista de compra #{lista.pk}',
    )
    return render(request, 'estoque/lista_compra/form.html', ctx)


@login_required
def modal_buscar_itens_lista_compra(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:lista_compra_estoque')
    return render(
        request,
        'estoque/partials/lista_compra_buscar_itens_modal.html',
        {},
    )


@login_required
def partial_buscar_itens_lista_compra(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:lista_compra_estoque')

    q = (request.GET.get('q') or '').strip()
    categoria_raw = (request.GET.get('categoria') or '').strip()

    if not q and not categoria_raw:
        return render(
            request,
            'estoque/lista_compra/_buscar_itens_lista.html',
            {
                'page_obj': [],
                'hint': 'Digite para buscar.',
            },
        )

    itens = (
        Item.objects.filter(empresa=empresa, ativo=True)
        .select_related('categoria', 'unidade_medida', 'fornecedor')
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
        'estoque/lista_compra/_buscar_itens_lista.html',
        {
            'page_obj': page_obj,
            'hint': '',
        },
    )


@login_required
def imprimir_lista_compra_estoque(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    lista = get_object_or_404(
        ListaCompraEstoque.objects.select_related('criado_por'),
        pk=pk,
        empresa=empresa,
    )
    itens = list(
        lista.itens.select_related(
            'item', 'item__unidade_medida', 'item__fornecedor'
        )
        .order_by('item__descricao', 'pk')
    )
    return render(
        request,
        'estoque/lista_compra/imprimir.html',
        {
            'lista': lista,
            'itens_lista': itens,
            'empresa': empresa,
        },
    )


@login_required
def imprimir_lista_compra_estoque_pdf(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    lista = get_object_or_404(
        ListaCompraEstoque.objects.select_related('criado_por'),
        pk=pk,
        empresa=empresa,
    )
    itens = list(
        lista.itens.select_related(
            'item', 'item__unidade_medida', 'item__fornecedor'
        )
        .order_by('item__descricao', 'pk')
    )
    from . import lista_compra_pdf

    data = lista_compra_pdf.build_lista_compra_pdf_bytes(empresa, lista, itens)
    resp = HttpResponse(data, content_type='application/pdf')
    raw_fn = ((lista.nome or '').strip() or str(lista.pk))[:60]
    safe = ''.join(c if c.isalnum() or c in '-_' else '_' for c in raw_fn) or str(lista.pk)
    resp['Content-Disposition'] = f'inline; filename="lista_compra_{lista.pk}_{safe}.pdf"'
    return resp


@login_required
def modal_excluir_lista_compra_estoque(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:lista_compra_estoque')

    lista = get_object_or_404(ListaCompraEstoque, pk=pk, empresa=empresa)
    excluir_url = reverse_empresa(
        request, 'estoque:excluir_lista_compra_estoque', kwargs={'pk': pk}
    )
    return render(
        request,
        'estoque/lista_compra/excluir_modal.html',
        {
            'lista': lista,
            'excluir_url': excluir_url,
        },
    )


@login_required
def excluir_lista_compra_estoque(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    lista = get_object_or_404(ListaCompraEstoque, pk=pk, empresa=empresa)

    if request.method != 'POST':
        return redirect_empresa(
            request, 'estoque:editar_lista_compra_estoque', kwargs={'pk': pk}
        )

    lid = lista.pk
    lista.delete()
    registrar_auditoria(
        request,
        acao='delete',
        resumo=f'Lista de compra #{lid} excluída.',
        modulo='estoque',
        detalhes={'lista_compra_id': lid},
    )
    messages.success(request, 'Lista de compra excluída.')

    if _is_htmx(request):
        return _hx_redirect_lista(request)
    return redirect_empresa(request, 'estoque:lista_compra_estoque')
