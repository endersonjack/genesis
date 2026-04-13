from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.registry import registrar_auditoria

from core.cadastro_copia import (
    EscolherEmpresaDestinoForm,
    copiar_obra_para_empresa,
    empresas_destino_para_copia,
    resposta_htmx_copia_sucesso,
)
from core.urlutils import redirect_empresa, reverse_empresa

from .forms import ObraForm
from .models import Obra


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

    itens = Obra.objects.filter(empresa=empresa).select_related('contratante')
    busca_q = (request.GET.get('q') or '').strip()
    if busca_q:
        digitos = ''.join(c for c in busca_q if c.isdigit())
        filtro = (
            Q(nome__icontains=busca_q)
            | Q(objeto__icontains=busca_q)
            | Q(endereco__icontains=busca_q)
            | Q(cno__icontains=busca_q)
            | Q(contratante__nome__icontains=busca_q)
        )
        if digitos:
            filtro |= Q(cno__icontains=digitos)
        itens = itens.filter(filtro)
    itens = itens.order_by('nome')
    return render(
        request,
        'obras/lista.html',
        {
            'page_title': 'Obras',
            'obras': itens,
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
        Obra.objects.select_related('contratante'),
        pk=pk,
        empresa=empresa,
    )
    return render(
        request,
        'obras/detalhe.html',
        {
            'page_title': item.nome,
            'obra': item,
        },
    )


@login_required
def modal_novo(request):
    return _modal_obra_form(request, item=None)


@login_required
def modal_editar(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    item = get_object_or_404(Obra, pk=pk, empresa=empresa)
    return _modal_obra_form(request, item=item)


@login_required
def modal_excluir_confirm(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item = get_object_or_404(Obra, pk=pk, empresa=empresa)

    if not _is_htmx(request):
        return redirect_empresa(request, 'obras:excluir', pk=pk)

    return render(
        request,
        'obras/partials/modal_excluir_confirm.html',
        {
            'obra': item,
            'excluir_url': reverse_empresa(request, 'obras:excluir', kwargs={'pk': pk}),
            'voltar_editar_url': reverse_empresa(
                request, 'obras:modal_editar', kwargs={'pk': pk}
            ),
        },
    )


def _modal_obra_form(request, item):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    if not empresa.clientes.exists():
        messages.warning(
            request,
            'Cadastre ao menos um cliente antes de registrar uma obra.',
        )
        if _is_htmx(request):
            resp = HttpResponse(status=200)
            resp['HX-Redirect'] = reverse_empresa(request, 'clientes:lista')
            return resp
        return redirect_empresa(request, 'clientes:lista')

    if not _is_htmx(request):
        return redirect_empresa(request, 'obras:lista')

    if item is None:
        post_url = reverse_empresa(request, 'obras:modal_novo')
        titulo_modal = 'Nova obra'
    else:
        post_url = reverse_empresa(request, 'obras:modal_editar', kwargs={'pk': item.pk})
        titulo_modal = f'Editar — {item.nome}'

    if request.method == 'POST':
        if item is not None:
            form = ObraForm(request.POST, instance=item, empresa=empresa)
        else:
            form = ObraForm(request.POST, empresa=empresa)
        if form.is_valid():
            if item is None:
                obj = form.save(commit=False)
                obj.empresa = empresa
                obj.save()
                registrar_auditoria(
                    request,
                    acao='create',
                    resumo=f'Obra «{obj.nome}» cadastrada.',
                    modulo='obras',
                )
                messages.success(request, 'Obra cadastrada com sucesso.')
            else:
                obj = form.save()
                registrar_auditoria(
                    request,
                    acao='update',
                    resumo=f'Obra «{obj.nome}» atualizada.',
                    modulo='obras',
                )
                messages.success(request, 'Obra atualizada com sucesso.')
            resp = HttpResponse(status=200)
            resp['HX-Redirect'] = reverse_empresa(request, 'obras:lista')
            return resp
    else:
        if item is not None:
            form = ObraForm(instance=item, empresa=empresa)
        else:
            form = ObraForm(empresa=empresa)

    return render(
        request,
        'obras/partials/modal_form_content.html',
        {
            'form': form,
            'post_url': post_url,
            'titulo_modal': titulo_modal,
            'obra_edicao': item,
        },
    )


@login_required
def criar(request):
    return redirect_empresa(request, 'obras:lista')


@login_required
def editar(request, pk):
    return redirect_empresa(request, 'obras:lista')


@login_required
def excluir(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item = get_object_or_404(Obra, pk=pk, empresa=empresa)
    if request.method == 'POST':
        nome = item.nome
        item.delete()
        registrar_auditoria(
            request,
            acao='delete',
            resumo=f'Obra «{nome}» excluída.',
            modulo='obras',
        )
        messages.success(request, 'Obra excluída.')
        if _is_htmx(request):
            resp = HttpResponse(status=200)
            resp['HX-Redirect'] = reverse_empresa(request, 'obras:lista')
            return resp
        return redirect_empresa(request, 'obras:lista')

    return render(
        request,
        'obras/confirmar_exclusao.html',
        {
            'page_title': 'Excluir obra',
            'obra': item,
        },
    )


def _ctx_modal_copiar_obra(request, item, pk, form=None, erro_copia=None):
    empresa = _empresa(request)
    qs_dest = empresas_destino_para_copia(request.user, empresa)
    sem_destino = not qs_dest.exists()
    valor_txt = '—'
    if item.valor is not None:
        valor_txt = (
            f'R$ {item.valor:,.2f}'.replace(',', 'v').replace('.', ',').replace('v', '.')
        )
    resumo = [
        {'label': 'Obra', 'valor': item.nome},
        {'label': 'Contratante', 'valor': item.contratante.nome},
        {'label': 'Valor', 'valor': valor_txt},
    ]
    return {
        'cadastro_label': 'Obra',
        'empresa_origem': empresa,
        'resumo_linhas': resumo,
        'copiar_post_url': reverse_empresa(request, 'obras:copiar', kwargs={'pk': pk}),
        'form': form,
        'sem_destino': sem_destino,
        'erro_copia': erro_copia,
    }


@login_required
def obra_modal_copiar(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    if not _is_htmx(request):
        return redirect_empresa(request, 'obras:detalhe', pk=pk)

    item = get_object_or_404(
        Obra.objects.select_related('contratante'), pk=pk, empresa=empresa
    )
    form = None
    if empresas_destino_para_copia(request.user, empresa).exists():
        form = EscolherEmpresaDestinoForm(user=request.user, empresa_origem=empresa)
    return render(
        request,
        'includes/cadastro_copiar_modal_inner.html',
        _ctx_modal_copiar_obra(request, item, pk, form=form),
    )


@login_required
def obra_copiar_executar(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    if not _is_htmx(request):
        return redirect_empresa(request, 'obras:detalhe', pk=pk)

    item = get_object_or_404(
        Obra.objects.select_related('contratante'), pk=pk, empresa=empresa
    )
    form = EscolherEmpresaDestinoForm(
        request.POST,
        user=request.user,
        empresa_origem=empresa,
    )
    if not form.is_valid():
        return render(
            request,
            'includes/cadastro_copiar_modal_inner.html',
            _ctx_modal_copiar_obra(request, item, pk, form=form),
            status=422,
        )
    dest = form.cleaned_data['empresa_destino']
    try:
        novo = copiar_obra_para_empresa(item, dest)
    except ValueError as exc:
        return render(
            request,
            'includes/cadastro_copiar_modal_inner.html',
            _ctx_modal_copiar_obra(
                request, item, pk, form=form, erro_copia=str(exc)
            ),
            status=422,
        )
    registrar_auditoria(
        request,
        acao='create',
        resumo=f'Obra «{novo.nome}» copiada para «{dest}».',
        modulo='obras',
        detalhes={
            'acao': 'copiar_cadastro',
            'origem_obra_id': item.pk,
            'destino_empresa_id': dest.pk,
            'nova_obra_id': novo.pk,
        },
    )
    messages.success(
        request,
        f'Obra «{novo.nome}» copiada com sucesso para «{dest}».',
    )
    return resposta_htmx_copia_sucesso()
