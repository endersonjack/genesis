from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.registry import registrar_auditoria

from core.urlutils import redirect_empresa, reverse_empresa

from .forms import CategoriaFerramentaForm, CategoriaItemForm, UnidadeMedidaForm
from .models import CategoriaFerramenta, CategoriaItem, Item, UnidadeMedida


def _empresa(request):
    return getattr(request, 'empresa_ativa', None)


def _is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def _hx_redirect_lista(request, lista_viewname: str):
    resp = HttpResponse(status=200)
    resp['HX-Redirect'] = reverse_empresa(request, lista_viewname)
    return resp


@login_required
def dashboard(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    qtd_itens = CategoriaItem.objects.filter(empresa=empresa).count()
    qtd_ferr = CategoriaFerramenta.objects.filter(empresa=empresa).count()
    qtd_unidades = UnidadeMedida.objects.filter(empresa=empresa).count()
    qtd_itens_cadastro = Item.objects.filter(empresa=empresa).count()

    return render(
        request,
        'estoque/dashboard.html',
        {
            'page_title': 'Estoque',
            'qtd_categorias_itens': qtd_itens,
            'qtd_categorias_ferramentas': qtd_ferr,
            'qtd_unidades_medida': qtd_unidades,
            'qtd_itens_cadastro': qtd_itens_cadastro,
        },
    )


@login_required
def lista_categorias_itens(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    q = (request.GET.get('q') or '').strip()
    itens = CategoriaItem.objects.filter(empresa=empresa).order_by('nome')
    if q:
        itens = itens.filter(nome__icontains=q)
    ctx = {
        'page_title': 'Categorias de itens',
        'categorias': itens,
        'q': q,
    }
    if _is_htmx(request):
        return render(request, 'estoque/categorias_itens/_lista_conteudo.html', ctx)
    return render(request, 'estoque/categorias_itens/lista.html', ctx)


@login_required
def modal_novo_categoria_item(request):
    return _modal_categoria_item_form(request, item=None)


@login_required
def modal_editar_categoria_item(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    categoria = get_object_or_404(CategoriaItem, pk=pk, empresa=empresa)
    return _modal_categoria_item_form(request, item=categoria)


def _modal_categoria_item_form(request, item):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:lista_categorias_itens')

    if item is None:
        post_url = reverse_empresa(request, 'estoque:modal_novo_categoria_item')
        titulo_modal = 'Nova categoria de item'
    else:
        post_url = reverse_empresa(
            request, 'estoque:modal_editar_categoria_item', kwargs={'pk': item.pk}
        )
        titulo_modal = f'Editar — {item.nome}'

    if request.method == 'POST':
        if item is not None:
            form = CategoriaItemForm(request.POST, instance=item, empresa=empresa)
        else:
            form = CategoriaItemForm(request.POST, empresa=empresa)
        if form.is_valid():
            try:
                obj = form.save()
            except IntegrityError:
                messages.error(request, 'Já existe uma categoria com este nome.')
            else:
                if item is None:
                    registrar_auditoria(
                        request,
                        acao='create',
                        resumo=f'Categoria de item «{obj.nome}» cadastrada.',
                        modulo='estoque',
                    )
                    messages.success(request, 'Categoria cadastrada.')
                else:
                    registrar_auditoria(
                        request,
                        acao='update',
                        resumo=f'Categoria de item «{obj.nome}» atualizada.',
                        modulo='estoque',
                    )
                    messages.success(request, 'Categoria atualizada.')
                return _hx_redirect_lista(request, 'estoque:lista_categorias_itens')
        else:
            messages.error(request, 'Revise o nome informado.')
    else:
        if item is not None:
            form = CategoriaItemForm(instance=item, empresa=empresa)
        else:
            form = CategoriaItemForm(empresa=empresa)

    ctx = {
        'form': form,
        'post_url': post_url,
        'titulo_modal': titulo_modal,
        'excluir_url': (
            reverse_empresa(
                request, 'estoque:modal_excluir_categoria_item', kwargs={'pk': item.pk}
            )
            if item
            else None
        ),
    }
    return render(request, 'estoque/partials/categoria_item_form_modal.html', ctx)


@login_required
def modal_excluir_categoria_item(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    categoria = get_object_or_404(CategoriaItem, pk=pk, empresa=empresa)
    if not _is_htmx(request):
        return redirect_empresa(
            request, 'estoque:excluir_categoria_item', kwargs={'pk': pk}
        )

    return render(
        request,
        'estoque/partials/categoria_item_excluir_modal.html',
        {
            'categoria': categoria,
            'excluir_url': reverse_empresa(
                request, 'estoque:excluir_categoria_item', kwargs={'pk': pk}
            ),
            'voltar_editar_url': reverse_empresa(
                request, 'estoque:modal_editar_categoria_item', kwargs={'pk': pk}
            ),
        },
    )


@login_required
def criar_categoria_item(request):
    return redirect_empresa(request, 'estoque:lista_categorias_itens')


@login_required
def editar_categoria_item(request, pk):
    return redirect_empresa(request, 'estoque:lista_categorias_itens')


@login_required
def excluir_categoria_item(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    categoria = get_object_or_404(CategoriaItem, pk=pk, empresa=empresa)
    if request.method == 'POST':
        nome = categoria.nome
        cid = categoria.pk
        categoria.delete()
        registrar_auditoria(
            request,
            acao='delete',
            resumo=f'Categoria de item «{nome}» excluída.',
            modulo='estoque',
            detalhes={'categoria_item_id': cid},
        )
        messages.success(request, 'Categoria excluída.')
        if _is_htmx(request):
            return _hx_redirect_lista(request, 'estoque:lista_categorias_itens')
        return redirect_empresa(request, 'estoque:lista_categorias_itens')

    return render(
        request,
        'estoque/categorias_itens/excluir.html',
        {
            'page_title': 'Excluir categoria',
            'categoria': categoria,
        },
    )


@login_required
def lista_categorias_ferramentas(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    q = (request.GET.get('q') or '').strip()
    itens = CategoriaFerramenta.objects.filter(empresa=empresa).order_by('nome')
    if q:
        itens = itens.filter(nome__icontains=q)
    ctx = {
        'page_title': 'Categorias de ferramentas',
        'categorias': itens,
        'q': q,
    }
    if _is_htmx(request):
        return render(request, 'estoque/categorias_ferramentas/_lista_conteudo.html', ctx)
    return render(request, 'estoque/categorias_ferramentas/lista.html', ctx)


@login_required
def modal_novo_categoria_ferramenta(request):
    return _modal_categoria_ferramenta_form(request, item=None)


@login_required
def modal_editar_categoria_ferramenta(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    categoria = get_object_or_404(CategoriaFerramenta, pk=pk, empresa=empresa)
    return _modal_categoria_ferramenta_form(request, item=categoria)


def _modal_categoria_ferramenta_form(request, item):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:lista_categorias_ferramentas')

    if item is None:
        post_url = reverse_empresa(request, 'estoque:modal_novo_categoria_ferramenta')
        titulo_modal = 'Nova categoria de ferramenta'
    else:
        post_url = reverse_empresa(
            request, 'estoque:modal_editar_categoria_ferramenta', kwargs={'pk': item.pk}
        )
        titulo_modal = f'Editar — {item.nome}'

    if request.method == 'POST':
        if item is not None:
            form = CategoriaFerramentaForm(request.POST, instance=item, empresa=empresa)
        else:
            form = CategoriaFerramentaForm(request.POST, empresa=empresa)
        if form.is_valid():
            try:
                obj = form.save()
            except IntegrityError:
                messages.error(request, 'Já existe uma categoria com este nome.')
            else:
                if item is None:
                    registrar_auditoria(
                        request,
                        acao='create',
                        resumo=f'Categoria de ferramenta «{obj.nome}» cadastrada.',
                        modulo='estoque',
                    )
                    messages.success(request, 'Categoria cadastrada.')
                else:
                    registrar_auditoria(
                        request,
                        acao='update',
                        resumo=f'Categoria de ferramenta «{obj.nome}» atualizada.',
                        modulo='estoque',
                    )
                    messages.success(request, 'Categoria atualizada.')
                return _hx_redirect_lista(request, 'estoque:lista_categorias_ferramentas')
        else:
            messages.error(request, 'Revise o nome informado.')
    else:
        if item is not None:
            form = CategoriaFerramentaForm(instance=item, empresa=empresa)
        else:
            form = CategoriaFerramentaForm(empresa=empresa)

    ctx = {
        'form': form,
        'post_url': post_url,
        'titulo_modal': titulo_modal,
        'excluir_url': (
            reverse_empresa(
                request,
                'estoque:modal_excluir_categoria_ferramenta',
                kwargs={'pk': item.pk},
            )
            if item
            else None
        ),
    }
    return render(request, 'estoque/partials/categoria_ferramenta_form_modal.html', ctx)


@login_required
def modal_excluir_categoria_ferramenta(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    categoria = get_object_or_404(CategoriaFerramenta, pk=pk, empresa=empresa)
    if not _is_htmx(request):
        return redirect_empresa(
            request, 'estoque:excluir_categoria_ferramenta', kwargs={'pk': pk}
        )

    return render(
        request,
        'estoque/partials/categoria_ferramenta_excluir_modal.html',
        {
            'categoria': categoria,
            'excluir_url': reverse_empresa(
                request, 'estoque:excluir_categoria_ferramenta', kwargs={'pk': pk}
            ),
            'voltar_editar_url': reverse_empresa(
                request, 'estoque:modal_editar_categoria_ferramenta', kwargs={'pk': pk}
            ),
        },
    )


@login_required
def criar_categoria_ferramenta(request):
    return redirect_empresa(request, 'estoque:lista_categorias_ferramentas')


@login_required
def editar_categoria_ferramenta(request, pk):
    return redirect_empresa(request, 'estoque:lista_categorias_ferramentas')


@login_required
def excluir_categoria_ferramenta(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    categoria = get_object_or_404(CategoriaFerramenta, pk=pk, empresa=empresa)
    if request.method == 'POST':
        nome = categoria.nome
        cid = categoria.pk
        categoria.delete()
        registrar_auditoria(
            request,
            acao='delete',
            resumo=f'Categoria de ferramenta «{nome}» excluída.',
            modulo='estoque',
            detalhes={'categoria_ferramenta_id': cid},
        )
        messages.success(request, 'Categoria excluída.')
        if _is_htmx(request):
            return _hx_redirect_lista(request, 'estoque:lista_categorias_ferramentas')
        return redirect_empresa(request, 'estoque:lista_categorias_ferramentas')

    return render(
        request,
        'estoque/categorias_ferramentas/excluir.html',
        {
            'page_title': 'Excluir categoria',
            'categoria': categoria,
        },
    )


@login_required
def lista_unidades_medida(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    q = (request.GET.get('q') or '').strip()
    unidades = UnidadeMedida.objects.filter(empresa=empresa).order_by('abreviada')
    if q:
        unidades = unidades.filter(
            Q(abreviada__icontains=q) | Q(completa__icontains=q)
        )
    ctx = {
        'page_title': 'Unidades de medida',
        'unidades': unidades,
        'q': q,
    }
    if _is_htmx(request):
        return render(request, 'estoque/unidades_medida/_lista_conteudo.html', ctx)
    return render(request, 'estoque/unidades_medida/lista.html', ctx)


@login_required
def modal_novo_unidade_medida(request):
    return _modal_unidade_medida_form(request, item=None)


@login_required
def modal_editar_unidade_medida(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    unidade = get_object_or_404(UnidadeMedida, pk=pk, empresa=empresa)
    return _modal_unidade_medida_form(request, item=unidade)


def _modal_unidade_medida_form(request, item):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:lista_unidades_medida')

    if item is None:
        post_url = reverse_empresa(request, 'estoque:modal_novo_unidade_medida')
        titulo_modal = 'Nova unidade de medida'
    else:
        post_url = reverse_empresa(
            request, 'estoque:modal_editar_unidade_medida', kwargs={'pk': item.pk}
        )
        titulo_modal = f'Editar — {item.abreviada}'

    if request.method == 'POST':
        if item is not None:
            form = UnidadeMedidaForm(request.POST, instance=item, empresa=empresa)
        else:
            form = UnidadeMedidaForm(request.POST, empresa=empresa)
        if form.is_valid():
            try:
                obj = form.save()
            except IntegrityError:
                messages.error(request, 'Já existe uma unidade com esta abreviação.')
            else:
                if item is None:
                    registrar_auditoria(
                        request,
                        acao='create',
                        resumo=f'Unidade de medida «{obj.abreviada}» ({obj.completa}) cadastrada.',
                        modulo='estoque',
                    )
                    messages.success(request, 'Unidade cadastrada.')
                else:
                    registrar_auditoria(
                        request,
                        acao='update',
                        resumo=f'Unidade de medida «{obj.abreviada}» ({obj.completa}) atualizada.',
                        modulo='estoque',
                    )
                    messages.success(request, 'Unidade atualizada.')
                return _hx_redirect_lista(request, 'estoque:lista_unidades_medida')
        else:
            messages.error(request, 'Revise os campos informados.')
    else:
        if item is not None:
            form = UnidadeMedidaForm(instance=item, empresa=empresa)
        else:
            form = UnidadeMedidaForm(empresa=empresa)

    ctx = {
        'form': form,
        'post_url': post_url,
        'titulo_modal': titulo_modal,
        'excluir_url': (
            reverse_empresa(
                request, 'estoque:modal_excluir_unidade_medida', kwargs={'pk': item.pk}
            )
            if item
            else None
        ),
    }
    return render(request, 'estoque/partials/unidade_medida_form_modal.html', ctx)


@login_required
def modal_excluir_unidade_medida(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    unidade = get_object_or_404(UnidadeMedida, pk=pk, empresa=empresa)
    if not _is_htmx(request):
        return redirect_empresa(
            request, 'estoque:excluir_unidade_medida', kwargs={'pk': pk}
        )

    return render(
        request,
        'estoque/partials/unidade_medida_excluir_modal.html',
        {
            'unidade': unidade,
            'excluir_url': reverse_empresa(
                request, 'estoque:excluir_unidade_medida', kwargs={'pk': pk}
            ),
            'voltar_editar_url': reverse_empresa(
                request, 'estoque:modal_editar_unidade_medida', kwargs={'pk': pk}
            ),
        },
    )


@login_required
def criar_unidade_medida(request):
    return redirect_empresa(request, 'estoque:lista_unidades_medida')


@login_required
def editar_unidade_medida(request, pk):
    return redirect_empresa(request, 'estoque:lista_unidades_medida')


@login_required
def excluir_unidade_medida(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    unidade = get_object_or_404(UnidadeMedida, pk=pk, empresa=empresa)
    if request.method == 'POST':
        abrev = unidade.abreviada
        uid = unidade.pk
        unidade.delete()
        registrar_auditoria(
            request,
            acao='delete',
            resumo=f'Unidade de medida «{abrev}» excluída.',
            modulo='estoque',
            detalhes={'unidade_medida_id': uid},
        )
        messages.success(request, 'Unidade excluída.')
        if _is_htmx(request):
            return _hx_redirect_lista(request, 'estoque:lista_unidades_medida')
        return redirect_empresa(request, 'estoque:lista_unidades_medida')

    return render(
        request,
        'estoque/unidades_medida/excluir.html',
        {
            'page_title': 'Excluir unidade',
            'unidade': unidade,
        },
    )
