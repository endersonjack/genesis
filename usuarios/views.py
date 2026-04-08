from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.urlutils import build_url_after_empresa_swap, is_safe_internal_path

from .models import UsuarioEmpresa


def _is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def _vinculos_usuario(request):
    return UsuarioEmpresa.objects.filter(
        usuario=request.user,
        ativo=True,
        empresa__ativa=True,
    ).select_related('empresa')


@login_required
def selecionar_empresa(request):
    vinculos = _vinculos_usuario(request)

    if request.method == 'POST':
        empresa_id = request.POST.get('empresa_id')
        vinculo = get_object_or_404(
            UsuarioEmpresa,
            usuario=request.user,
            empresa_id=empresa_id,
            ativo=True,
            empresa__ativa=True
        )
        request.session['empresa_id'] = vinculo.empresa.id
        return redirect('dashboard_home', empresa_id=vinculo.empresa.id)

    return render(request, 'usuarios/selecionar_empresa.html', {
        'vinculos': vinculos,
        'empresa_sessao_id': request.session.get('empresa_id'),
    })


@login_required
def pagina_trocar_empresa_legacy(request):
    """Antiga URL global; redireciona para a rota escopada em /empresa/<id>/."""
    eid = request.session.get('empresa_id')
    if eid:
        return redirect('trocar_empresa_pagina', empresa_id=eid)
    return redirect('selecionar_empresa')


@login_required
def pagina_trocar_empresa(request, empresa_id):
    """
    Página sob /empresa/<id>/ para manter empresa ativa no contexto (topbar/sidebar).
    Com uma única empresa, redireciona — o menu não deve expor este link.
    """
    vinculos = _vinculos_usuario(request)
    if vinculos.count() <= 1:
        v = vinculos.first()
        if v:
            return redirect('dashboard_home', empresa_id=v.empresa_id)
        return redirect('selecionar_empresa')

    next_path = request.GET.get('next')
    if not next_path or not is_safe_internal_path(next_path):
        next_path = reverse('dashboard_home', kwargs={'empresa_id': empresa_id})
    empresa_sessao_id = (
        getattr(getattr(request, 'empresa_ativa', None), 'pk', None)
        or request.session.get('empresa_id')
    )
    return render(request, 'usuarios/trocar_empresa_pagina.html', {
        'vinculos': vinculos,
        'next_path': next_path,
        'empresa_sessao_id': empresa_sessao_id,
    })


@login_required
def modal_trocar_empresa(request):
    vinculos = _vinculos_usuario(request)
    next_path = request.GET.get('next') or request.path
    if not is_safe_internal_path(next_path):
        next_path = '/'
    empresa_sessao_id = (
        getattr(getattr(request, 'empresa_ativa', None), 'pk', None)
        or request.session.get('empresa_id')
    )
    return render(request, 'usuarios/_modal_trocar_empresa.html', {
        'vinculos': vinculos,
        'next_path': next_path,
        'empresa_sessao_id': empresa_sessao_id,
    })


@login_required
def trocar_empresa(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    empresa_id = request.POST.get('empresa_id')
    next_path = request.POST.get('next') or ''
    if not is_safe_internal_path(next_path):
        next_path = ''

    vinculo = get_object_or_404(
        UsuarioEmpresa,
        usuario=request.user,
        empresa_id=empresa_id,
        ativo=True,
        empresa__ativa=True,
    )
    request.session['empresa_id'] = vinculo.empresa.id

    new_url = build_url_after_empresa_swap(next_path, vinculo.empresa.id)
    if not new_url:
        new_url = reverse('dashboard_home', kwargs={'empresa_id': vinculo.empresa.id})

    if _is_htmx(request):
        response = HttpResponse(status=200)
        response['HX-Redirect'] = new_url
        return response
    return redirect(new_url)