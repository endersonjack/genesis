from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.empresa_access import usuario_e_so_apontador
from core.urlutils import build_url_after_empresa_swap, is_safe_internal_path

from auditoria.registry import registrar_auditoria

from .forms import MeuPerfilForm
from .models import UsuarioEmpresa


def _is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def _vinculos_usuario(request):
    return UsuarioEmpresa.objects.filter(
        usuario=request.user,
        ativo=True,
        empresa__ativa=True,
    ).select_related('empresa')


def _empresa_sessao_para_auditoria(request):
    """Empresa da sessão com vínculo ativo (rota global sem `empresa_ativa` no request)."""
    eid = request.session.get('empresa_id')
    if not eid:
        return None
    v = (
        UsuarioEmpresa.objects.filter(
            usuario=request.user,
            empresa_id=eid,
            ativo=True,
            empresa__ativa=True,
        )
        .select_related('empresa')
        .first()
    )
    return v.empresa if v else None


@login_required
def meu_perfil(request):
    """Dados da conta: nome, login, senha e foto (rota global /usuarios/perfil/)."""
    if request.method == 'POST':
        User = get_user_model()
        antes = User.objects.get(pk=request.user.pk)
        nome_antes = antes.nome_completo or ''
        username_antes = antes.username or ''
        foto_antes = antes.foto.name if antes.foto else ''

        form = MeuPerfilForm(
            request.POST,
            request.FILES,
            instance=request.user,
        )
        if form.is_valid():
            user = form.save()
            if form.cleaned_data.get('nova_senha'):
                update_session_auth_hash(request, user)

            empresa_audit = getattr(request, 'empresa_ativa', None) or _empresa_sessao_para_auditoria(
                request
            )
            if empresa_audit:
                detalhes: dict = {}
                if (user.nome_completo or '') != nome_antes:
                    detalhes['nome_completo'] = {'de': nome_antes, 'para': user.nome_completo or ''}
                if user.username != username_antes:
                    detalhes['username'] = {'de': username_antes, 'para': user.username}
                foto_depois = user.foto.name if user.foto else ''
                if foto_depois != foto_antes:
                    detalhes['foto'] = {'de': foto_antes or None, 'para': foto_depois or None}
                if form.cleaned_data.get('nova_senha'):
                    detalhes['senha'] = 'alterada'
                if detalhes:
                    registrar_auditoria(
                        request,
                        acao='update',
                        resumo=f'Perfil da conta atualizado ({user.username}).',
                        modulo='usuarios',
                        detalhes=detalhes,
                        empresa=empresa_audit,
                    )

            messages.success(request, 'Perfil atualizado com sucesso.')
            return redirect('meu_perfil')
    else:
        form = MeuPerfilForm(instance=request.user)

    return render(
        request,
        'usuarios/meu_perfil.html',
        {'form': form},
    )


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
        if usuario_e_so_apontador(request.user, vinculo):
            return redirect('apontamento:home', empresa_id=vinculo.empresa.id)
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
            if usuario_e_so_apontador(request.user, v):
                return redirect('apontamento:home', empresa_id=v.empresa_id)
            return redirect('dashboard_home', empresa_id=v.empresa_id)
        return redirect('selecionar_empresa')

    next_path = request.GET.get('next')
    if not next_path or not is_safe_internal_path(next_path):
        v_padrao = vinculos.filter(empresa_id=empresa_id).first()
        if v_padrao and usuario_e_so_apontador(request.user, v_padrao):
            next_path = reverse('apontamento:home', kwargs={'empresa_id': empresa_id})
        else:
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

    if usuario_e_so_apontador(request.user, vinculo):
        dash = reverse('dashboard_home', kwargs={'empresa_id': vinculo.empresa.id})
        ap_home = reverse('apontamento:home', kwargs={'empresa_id': vinculo.empresa.id})
        if new_url.rstrip('/') == dash.rstrip('/'):
            new_url = ap_home

    if _is_htmx(request):
        response = HttpResponse(status=200)
        response['HX-Redirect'] = new_url
        return response
    return redirect(new_url)