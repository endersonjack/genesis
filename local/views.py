from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.registry import registrar_auditoria

from core.urlutils import redirect_empresa, reverse_empresa

from .forms import LocalForm
from .models import Local


def _is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def _redirect_lista_htmx(request):
    response = HttpResponse(status=200)
    response['HX-Redirect'] = reverse_empresa(request, 'local:lista')
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
            registrar_auditoria(
                request,
                acao='create',
                resumo=f'Local "{obj.nome}" cadastrado.',
                modulo='local',
                detalhes={'local_id': obj.pk},
            )
            messages.success(request, f'Local "{obj.nome}" cadastrado com sucesso.')
            if _is_htmx(request):
                return _redirect_lista_htmx(request)
            return redirect_empresa(request, 'local:lista')
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
            salvo = form.save()
            registrar_auditoria(
                request,
                acao='update',
                resumo=f'Local "{salvo.nome}" atualizado.',
                modulo='local',
                detalhes={'local_id': salvo.pk},
            )
            messages.success(request, f'Local "{salvo.nome}" atualizado com sucesso.')
            if _is_htmx(request):
                return _redirect_lista_htmx(request)
            return redirect_empresa(request, 'local:lista')
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
        local_id = local.pk
        local.delete()
        registrar_auditoria(
            request,
            acao='delete',
            resumo=f'Local "{nome}" excluído.',
            modulo='local',
            detalhes={'local_id': local_id},
        )
        messages.success(request, f'Local "{nome}" excluído com sucesso.')
        if _is_htmx(request):
            return _redirect_lista_htmx(request)
        return redirect_empresa(request, 'local:lista')

    return render(
        request,
        'local/_excluir_modal.html',
        {'local': local},
    )
