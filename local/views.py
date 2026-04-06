from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import LocalForm
from .models import Local


def _is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def _redirect_lista_htmx():
    response = HttpResponse(status=200)
    response['HX-Redirect'] = reverse('local:lista')
    return response


@login_required
def lista_locais(request):
    empresa = getattr(request, 'empresa_ativa', None)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa para gerenciar os locais.')
        return redirect('selecionar_empresa')

    locais = Local.objects.filter(empresa=empresa).order_by('nome')
    return render(
        request,
        'local/lista.html',
        {
            'page_title': 'Locais',
            'locais': locais,
        },
    )


@login_required
def local_criar(request):
    empresa = getattr(request, 'empresa_ativa', None)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    form = LocalForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa
            obj.save()
            messages.success(request, f'Local "{obj.nome}" cadastrado com sucesso.')
            if _is_htmx(request):
                return _redirect_lista_htmx()
            return redirect('local:lista')
        messages.error(request, 'Revise os campos do formulário.')

    return render(
        request,
        'local/_form_modal.html',
        {
            'form': form,
            'modo': 'criar',
            'local': None,
        },
    )


@login_required
def local_editar(request, pk):
    empresa = getattr(request, 'empresa_ativa', None)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    local = get_object_or_404(Local, pk=pk, empresa=empresa)
    form = LocalForm(request.POST or None, instance=local)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, f'Local "{local.nome}" atualizado com sucesso.')
            if _is_htmx(request):
                return _redirect_lista_htmx()
            return redirect('local:lista')
        messages.error(request, 'Revise os campos do formulário.')

    return render(
        request,
        'local/_form_modal.html',
        {
            'form': form,
            'modo': 'editar',
            'local': local,
        },
    )


@login_required
def local_excluir(request, pk):
    empresa = getattr(request, 'empresa_ativa', None)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    local = get_object_or_404(Local, pk=pk, empresa=empresa)

    if request.method == 'POST':
        nome = local.nome
        local.delete()
        messages.success(request, f'Local "{nome}" excluído com sucesso.')
        if _is_htmx(request):
            return _redirect_lista_htmx()
        return redirect('local:lista')

    return render(
        request,
        'local/_excluir_modal.html',
        {'local': local},
    )
