import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.registry import registrar_auditoria

from core.cadastro_copia import (
    EscolherEmpresaDestinoForm,
    copiar_fornecedor_para_empresa,
    empresas_destino_para_copia,
    resposta_htmx_copia_sucesso,
)
from core.urlutils import redirect_empresa, reverse_empresa

from .forms import FornecedorForm, FornecedorQuickCreateForm
from .models import Fornecedor


def _empresa(request):
    return getattr(request, 'empresa_ativa', None)


def _is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


@login_required
def lista(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    itens = Fornecedor.objects.filter(empresa=empresa).select_related('categoria', 'banco')
    busca_q = (request.GET.get('q') or '').strip()
    if busca_q:
        digitos = ''.join(c for c in busca_q if c.isdigit())
        filtro = Q(nome__icontains=busca_q) | Q(razao_social__icontains=busca_q)
        if digitos:
            filtro |= Q(cpf_cnpj__icontains=digitos)
        itens = itens.filter(filtro)
    itens = itens.order_by('nome')
    return render(
        request,
        'fornecedores/lista.html',
        {
            'page_title': 'Fornecedores',
            'fornecedores': itens,
            'busca_q': busca_q,
        },
    )


@login_required
def detalhe(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item = get_object_or_404(
        Fornecedor.objects.select_related('categoria', 'banco'),
        pk=pk,
        empresa=empresa,
    )
    return render(
        request,
        'fornecedores/detalhe.html',
        {
            'page_title': item.nome,
            'fornecedor': item,
        },
    )


@login_required
def modal_novo(request):
    return _modal_fornecedor_form(request, item=None)


@login_required
def modal_novo_rapido(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    if not _is_htmx(request):
        return redirect_empresa(request, 'fornecedores:lista')

    post_url = reverse_empresa(request, 'fornecedores:modal_novo_rapido')
    if request.method == 'POST':
        form = FornecedorQuickCreateForm(request.POST, empresa=empresa)
        if form.is_valid():
            obj = form.save()
            registrar_auditoria(
                request,
                acao='create',
                resumo=f'Fornecedor "{obj.nome}" cadastrado rapidamente.',
                modulo='fornecedores',
            )
            payload = json.dumps(
                {
                    'id': obj.pk,
                    'nome': obj.nome,
                    'razao_social': obj.razao_social,
                    'cpf_cnpj': obj.cpf_cnpj,
                    'cpf_cnpj_formatado': obj.cpf_cnpj_formatado,
                }
            ).replace('<', '\\u003c')
            resp = HttpResponse(
                (
                    '<div class="modal-body text-center py-4">'
                    '<div class="spinner-border text-primary" role="status">'
                    '<span class="visually-hidden">Selecionando...</span>'
                    '</div>'
                    '</div>'
                    '<script>'
                    '(function () {'
                    f'var fornecedor = {payload};'
                    'if (window.selecionarFornecedorPagamentoNf) {'
                    'window.selecionarFornecedorPagamentoNf(fornecedor);'
                    '}'
                    '})();'
                    '</script>'
                ),
                status=200,
            )
            resp['HX-Trigger'] = json.dumps(
                {
                    'fornecedorCriadoRapido': {
                        'id': obj.pk,
                        'nome': obj.nome,
                        'razao_social': obj.razao_social,
                        'cpf_cnpj': obj.cpf_cnpj,
                        'cpf_cnpj_formatado': obj.cpf_cnpj_formatado,
                    }
                }
            )
            return resp
    else:
        form = FornecedorQuickCreateForm(empresa=empresa)

    return render(
        request,
        'fornecedores/partials/modal_form_rapido_nf.html',
        {
            'form': form,
            'post_url': post_url,
        },
    )


@login_required
def modal_editar(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    item = get_object_or_404(Fornecedor, pk=pk, empresa=empresa)
    return _modal_fornecedor_form(request, item=item)


@login_required
def modal_excluir_confirm(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item = get_object_or_404(Fornecedor, pk=pk, empresa=empresa)

    if not _is_htmx(request):
        return redirect_empresa(request, 'fornecedores:excluir', pk=pk)

    return render(
        request,
        'fornecedores/partials/modal_excluir_confirm.html',
        {
            'fornecedor': item,
            'excluir_url': reverse_empresa(request, 'fornecedores:excluir', kwargs={'pk': pk}),
            'voltar_editar_url': reverse_empresa(
                request, 'fornecedores:modal_editar', kwargs={'pk': pk}
            ),
        },
    )


def _modal_fornecedor_form(request, item):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    if not _is_htmx(request):
        return redirect_empresa(request, 'fornecedores:lista')

    if item is None:
        post_url = reverse_empresa(request, 'fornecedores:modal_novo')
        titulo_modal = 'Novo fornecedor'
    else:
        post_url = reverse_empresa(request, 'fornecedores:modal_editar', kwargs={'pk': item.pk})
        titulo_modal = f'Editar — {item.nome}'

    if request.method == 'POST':
        if item is not None:
            form = FornecedorForm(request.POST, instance=item, empresa=empresa)
        else:
            form = FornecedorForm(request.POST, empresa=empresa)
        if form.is_valid():
            if item is None:
                obj = form.save(commit=False)
                obj.empresa = empresa
                obj.save()
                registrar_auditoria(
                    request,
                    acao='create',
                    resumo=f'Fornecedor "{obj.nome}" cadastrado.',
                    modulo='fornecedores',
                )
                messages.success(request, 'Fornecedor cadastrado com sucesso.')
            else:
                obj = form.save()
                registrar_auditoria(
                    request,
                    acao='update',
                    resumo=f'Fornecedor "{obj.nome}" atualizado.',
                    modulo='fornecedores',
                )
                messages.success(request, 'Fornecedor atualizado com sucesso.')
            resp = HttpResponse(status=200)
            resp['HX-Redirect'] = reverse_empresa(request, 'fornecedores:lista')
            return resp
    else:
        if item is not None:
            form = FornecedorForm(instance=item, empresa=empresa)
        else:
            form = FornecedorForm(empresa=empresa)

    return render(
        request,
        'fornecedores/partials/modal_form_content.html',
        {
            'form': form,
            'post_url': post_url,
            'titulo_modal': titulo_modal,
            'fornecedor_edicao': item,
        },
    )


@login_required
def criar(request):
    return redirect_empresa(request, 'fornecedores:lista')


@login_required
def editar(request, pk):
    return redirect_empresa(request, 'fornecedores:lista')


@login_required
def excluir(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item = get_object_or_404(Fornecedor, pk=pk, empresa=empresa)
    if request.method == 'POST':
        nome = item.nome
        item.delete()
        registrar_auditoria(
            request,
            acao='delete',
            resumo=f'Fornecedor "{nome}" excluído.',
            modulo='fornecedores',
        )
        messages.success(request, 'Fornecedor excluído.')
        if _is_htmx(request):
            resp = HttpResponse(status=200)
            resp['HX-Redirect'] = reverse_empresa(request, 'fornecedores:lista')
            return resp
        return redirect_empresa(request, 'fornecedores:lista')

    return render(
        request,
        'fornecedores/confirmar_exclusao.html',
        {
            'page_title': 'Excluir fornecedor',
            'fornecedor': item,
        },
    )


def _ctx_modal_copiar_fornecedor(request, item, pk, form=None, erro_copia=None):
    empresa = _empresa(request)
    qs_dest = empresas_destino_para_copia(request.user, empresa)
    sem_destino = not qs_dest.exists()
    resumo = [
        {'label': 'Nome', 'valor': item.nome},
        {'label': 'CPF/CNPJ', 'valor': item.cpf_cnpj_formatado},
        {'label': 'Tipo', 'valor': item.get_tipo_display()},
    ]
    return {
        'cadastro_label': 'Fornecedor',
        'empresa_origem': empresa,
        'resumo_linhas': resumo,
        'copiar_post_url': reverse_empresa(
            request, 'fornecedores:copiar', kwargs={'pk': pk}
        ),
        'form': form,
        'sem_destino': sem_destino,
        'erro_copia': erro_copia,
    }


@login_required
def fornecedor_modal_copiar(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    if not _is_htmx(request):
        return redirect_empresa(request, 'fornecedores:detalhe', pk=pk)

    item = get_object_or_404(Fornecedor, pk=pk, empresa=empresa)
    form = None
    if empresas_destino_para_copia(request.user, empresa).exists():
        form = EscolherEmpresaDestinoForm(user=request.user, empresa_origem=empresa)
    return render(
        request,
        'includes/cadastro_copiar_modal_inner.html',
        _ctx_modal_copiar_fornecedor(request, item, pk, form=form),
    )


@login_required
def fornecedor_copiar_executar(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    if not _is_htmx(request):
        return redirect_empresa(request, 'fornecedores:detalhe', pk=pk)

    item = get_object_or_404(Fornecedor, pk=pk, empresa=empresa)
    form = EscolherEmpresaDestinoForm(
        request.POST,
        user=request.user,
        empresa_origem=empresa,
    )
    if not form.is_valid():
        return render(
            request,
            'includes/cadastro_copiar_modal_inner.html',
            _ctx_modal_copiar_fornecedor(request, item, pk, form=form),
            status=422,
        )
    dest = form.cleaned_data['empresa_destino']
    try:
        novo = copiar_fornecedor_para_empresa(item, dest)
    except ValueError as exc:
        return render(
            request,
            'includes/cadastro_copiar_modal_inner.html',
            _ctx_modal_copiar_fornecedor(
                request, item, pk, form=form, erro_copia=str(exc)
            ),
            status=422,
        )
    registrar_auditoria(
        request,
        acao='create',
        resumo=f'Fornecedor «{novo.nome}» copiado para «{dest}».',
        modulo='fornecedores',
        detalhes={
            'acao': 'copiar_cadastro',
            'origem_fornecedor_id': item.pk,
            'destino_empresa_id': dest.pk,
            'novo_fornecedor_id': novo.pk,
        },
    )
    messages.success(
        request,
        f'Fornecedor «{novo.nome}» copiado com sucesso para «{dest}».',
    )
    return resposta_htmx_copia_sucesso()
