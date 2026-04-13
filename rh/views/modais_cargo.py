"""
Modais HTMX para criar, editar e excluir cargos.

A listagem permanece na página `lista_cargos`; após sucesso, HX-Redirect para ela.
"""

from urllib.parse import urlencode

from django.contrib import messages
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from auditoria.registry import audit_rh
from core.urlutils import reverse_empresa

from ..forms import CargoForm
from ..models import Cargo
from .base import _empresa_ativa_or_redirect


def _hx_redirect_lista_cargos(request, return_q: str = '') -> HttpResponse:
    path = reverse_empresa(request, 'rh:lista_cargos')
    q = (return_q or '').strip()
    if q:
        path = f'{path}?{urlencode({"q": q})}'
    response = HttpResponse(status=204)
    response['HX-Redirect'] = path
    return response


def modal_cargo_criar(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de criar um cargo.',
    )
    if redirect_response:
        return redirect_response

    if request.method == 'POST':
        form = CargoForm(request.POST, empresa_ativa=empresa_ativa)
        return_q = (request.POST.get('return_q') or '').strip()
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa_ativa
            obj.save()
            audit_rh(
                request,
                'create',
                f'Cargo "{obj.nome}" criado (modal).',
                {'cargo_id': obj.pk},
            )
            messages.success(request, 'Cargo criado com sucesso.')
            return _hx_redirect_lista_cargos(request, return_q=return_q)
    else:
        form = CargoForm(empresa_ativa=empresa_ativa)
        return_q = (request.GET.get('q') or '').strip()

    return render(
        request,
        'rh/cargos/modals/modal_cargo_form.html',
        {
            'form': form,
            'titulo': 'Novo cargo',
            'modo': 'criar',
            'cargo': None,
            'return_q': return_q,
        },
    )


def modal_cargo_editar(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de editar um cargo.',
    )
    if redirect_response:
        return redirect_response

    cargo = get_object_or_404(Cargo, pk=pk, empresa=empresa_ativa)

    if request.method == 'POST':
        form = CargoForm(
            request.POST,
            instance=cargo,
            empresa_ativa=empresa_ativa,
        )
        return_q = (request.POST.get('return_q') or '').strip()
        if form.is_valid():
            salvo = form.save()
            audit_rh(
                request,
                'update',
                f'Cargo "{salvo.nome}" atualizado (modal).',
                {'cargo_id': salvo.pk},
            )
            messages.success(request, 'Cargo atualizado com sucesso.')
            return _hx_redirect_lista_cargos(request, return_q=return_q)
    else:
        form = CargoForm(instance=cargo, empresa_ativa=empresa_ativa)
        return_q = (request.GET.get('q') or '').strip()

    return render(
        request,
        'rh/cargos/modals/modal_cargo_form.html',
        {
            'form': form,
            'titulo': 'Editar cargo',
            'modo': 'editar',
            'cargo': cargo,
            'return_q': return_q,
        },
    )


def modal_cargo_excluir(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de excluir um cargo.',
    )
    if redirect_response:
        return redirect_response

    cargo = get_object_or_404(
        Cargo.objects.annotate(total_funcionarios=Count('funcionarios', distinct=True)),
        pk=pk,
        empresa=empresa_ativa,
    )

    if request.method == 'POST':
        return_q = (request.POST.get('return_q') or '').strip()
        nome = cargo.nome
        cid = cargo.pk
        cargo.delete()
        audit_rh(
            request,
            'delete',
            f'Cargo "{nome}" excluído (modal).',
            {'cargo_id': cid},
        )
        messages.success(request, 'Cargo excluído com sucesso.')
        return _hx_redirect_lista_cargos(request, return_q=return_q)

    return render(
        request,
        'rh/cargos/modals/modal_cargo_excluir.html',
        {
            'cargo': cargo,
            'return_q': (request.GET.get('q') or '').strip(),
        },
    )
