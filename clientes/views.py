from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.registry import registrar_auditoria

from core.cadastro_copia import (
    EscolherEmpresaDestinoForm,
    copiar_cliente_para_empresa,
    empresas_destino_para_copia,
    resposta_htmx_copia_sucesso,
)
from core.urlutils import redirect_empresa, reverse_empresa

from .forms import ClienteForm
from .models import Cliente


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

    itens = Cliente.objects.filter(empresa=empresa)
    busca_q = (request.GET.get('q') or '').strip()
    if busca_q:
        digitos = ''.join(c for c in busca_q if c.isdigit())
        filtro = (
            Q(nome__icontains=busca_q)
            | Q(razao_social__icontains=busca_q)
            | Q(email__icontains=busca_q)
        )
        if digitos:
            filtro |= Q(telefone__icontains=digitos) | Q(cpf_cnpj__icontains=digitos)
        itens = itens.filter(filtro)
    itens = itens.order_by('nome')
    return render(
        request,
        'clientes/lista.html',
        {
            'page_title': 'Clientes',
            'clientes': itens,
            'busca_q': busca_q,
        },
    )


@login_required
def detalhe(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item = get_object_or_404(Cliente, pk=pk, empresa=empresa)
    return render(
        request,
        'clientes/detalhe.html',
        {
            'page_title': item.nome,
            'cliente': item,
        },
    )


@login_required
def modal_novo(request):
    return _modal_cliente_form(request, item=None)


@login_required
def modal_editar(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    item = get_object_or_404(Cliente, pk=pk, empresa=empresa)
    return _modal_cliente_form(request, item=item)


@login_required
def modal_excluir_confirm(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item = get_object_or_404(Cliente, pk=pk, empresa=empresa)

    if not _is_htmx(request):
        return redirect_empresa(request, 'clientes:excluir', pk=pk)

    return render(
        request,
        'clientes/partials/modal_excluir_confirm.html',
        {
            'cliente': item,
            'excluir_url': reverse_empresa(request, 'clientes:excluir', kwargs={'pk': pk}),
            'voltar_editar_url': reverse_empresa(
                request, 'clientes:modal_editar', kwargs={'pk': pk}
            ),
        },
    )


def _modal_cliente_form(request, item):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    if not _is_htmx(request):
        return redirect_empresa(request, 'clientes:lista')

    if item is None:
        post_url = reverse_empresa(request, 'clientes:modal_novo')
        titulo_modal = 'Novo cliente'
    else:
        post_url = reverse_empresa(request, 'clientes:modal_editar', kwargs={'pk': item.pk})
        titulo_modal = f'Editar — {item.nome}'

    if request.method == 'POST':
        if item is not None:
            form = ClienteForm(request.POST, instance=item, empresa=empresa)
        else:
            form = ClienteForm(request.POST, empresa=empresa)
        if form.is_valid():
            if item is None:
                obj = form.save(commit=False)
                obj.empresa = empresa
                obj.save()
                registrar_auditoria(
                    request,
                    acao='create',
                    resumo=f'Cliente "{obj.nome}" cadastrado.',
                    modulo='clientes',
                )
                messages.success(request, 'Cliente cadastrado com sucesso.')
            else:
                obj = form.save()
                registrar_auditoria(
                    request,
                    acao='update',
                    resumo=f'Cliente "{obj.nome}" atualizado.',
                    modulo='clientes',
                )
                messages.success(request, 'Cliente atualizado com sucesso.')
            resp = HttpResponse(status=200)
            resp['HX-Redirect'] = reverse_empresa(request, 'clientes:lista')
            return resp
    else:
        if item is not None:
            form = ClienteForm(instance=item, empresa=empresa)
        else:
            form = ClienteForm(empresa=empresa)

    return render(
        request,
        'clientes/partials/modal_form_content.html',
        {
            'form': form,
            'post_url': post_url,
            'titulo_modal': titulo_modal,
            'cliente_edicao': item,
        },
    )


@login_required
def criar(request):
    return redirect_empresa(request, 'clientes:lista')


@login_required
def editar(request, pk):
    return redirect_empresa(request, 'clientes:lista')


@login_required
def excluir(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item = get_object_or_404(Cliente, pk=pk, empresa=empresa)
    if request.method == 'POST':
        nome = item.nome
        item.delete()
        registrar_auditoria(
            request,
            acao='delete',
            resumo=f'Cliente "{nome}" excluído.',
            modulo='clientes',
        )
        messages.success(request, 'Cliente excluído.')
        if _is_htmx(request):
            resp = HttpResponse(status=200)
            resp['HX-Redirect'] = reverse_empresa(request, 'clientes:lista')
            return resp
        return redirect_empresa(request, 'clientes:lista')

    return render(
        request,
        'clientes/confirmar_exclusao.html',
        {
            'page_title': 'Excluir cliente',
            'cliente': item,
        },
    )


def _ctx_modal_copiar_cliente(request, item, pk, form=None, erro_copia=None):
    empresa = _empresa(request)
    qs_dest = empresas_destino_para_copia(request.user, empresa)
    sem_destino = not qs_dest.exists()
    resumo = [
        {'label': 'Nome', 'valor': item.nome},
        {'label': 'Tipo', 'valor': item.get_tipo_display()},
        {
            'label': 'CPF/CNPJ',
            'valor': item.cpf_cnpj_formatado,
        },
    ]
    return {
        'cadastro_label': 'Cliente',
        'empresa_origem': empresa,
        'resumo_linhas': resumo,
        'copiar_post_url': reverse_empresa(request, 'clientes:copiar', kwargs={'pk': pk}),
        'form': form,
        'sem_destino': sem_destino,
        'erro_copia': erro_copia,
    }


@login_required
def cliente_modal_copiar(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    if not _is_htmx(request):
        return redirect_empresa(request, 'clientes:detalhe', pk=pk)

    item = get_object_or_404(Cliente, pk=pk, empresa=empresa)
    form = None
    if empresas_destino_para_copia(request.user, empresa).exists():
        form = EscolherEmpresaDestinoForm(user=request.user, empresa_origem=empresa)
    return render(
        request,
        'includes/cadastro_copiar_modal_inner.html',
        _ctx_modal_copiar_cliente(request, item, pk, form=form),
    )


@login_required
def cliente_copiar_executar(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    if not _is_htmx(request):
        return redirect_empresa(request, 'clientes:detalhe', pk=pk)

    item = get_object_or_404(Cliente, pk=pk, empresa=empresa)
    form = EscolherEmpresaDestinoForm(
        request.POST,
        user=request.user,
        empresa_origem=empresa,
    )
    if not form.is_valid():
        return render(
            request,
            'includes/cadastro_copiar_modal_inner.html',
            _ctx_modal_copiar_cliente(request, item, pk, form=form),
            status=422,
        )
    dest = form.cleaned_data['empresa_destino']
    try:
        novo = copiar_cliente_para_empresa(item, dest)
    except ValueError as exc:
        return render(
            request,
            'includes/cadastro_copiar_modal_inner.html',
            _ctx_modal_copiar_cliente(
                request, item, pk, form=form, erro_copia=str(exc)
            ),
            status=422,
        )
    registrar_auditoria(
        request,
        acao='create',
        resumo=f'Cliente «{novo.nome}» copiado para «{dest}».',
        modulo='clientes',
        detalhes={
            'acao': 'copiar_cadastro',
            'origem_cliente_id': item.pk,
            'destino_empresa_id': dest.pk,
            'novo_cliente_id': novo.pk,
        },
    )
    messages.success(
        request,
        f'Cliente «{novo.nome}» copiado com sucesso para «{dest}».',
    )
    return resposta_htmx_copia_sucesso()
