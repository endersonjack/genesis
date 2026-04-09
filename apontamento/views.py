from functools import wraps
from typing import Optional

from django.contrib import messages
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from local.models import Local
from rh.models import Funcionario
from rh.views.base import _empresa_ativa_or_redirect

from .forms import ApontamentoFaltaForm, ApontamentoObservacaoLocalForm
from .models import ApontamentoFalta, ApontamentoObservacaoLocal, StatusApontamento
from .permissions import usuario_rh_pode_gerir_status_apontamento


def _ctx_status_apontamento_mobile(request: HttpRequest) -> dict:
    return {
        'pode_gerir_status_apontamento': usuario_rh_pode_gerir_status_apontamento(
            request
        ),
        'status_apontamento_choices': StatusApontamento.choices,
    }


def _is_htmx(request: HttpRequest) -> bool:
    return request.headers.get('HX-Request') == 'true'


def _parse_edit_pk(request: HttpRequest, *, post: bool) -> Optional[int]:
    raw = ((request.POST if post else request.GET).get('edit_pk') or '').strip()
    if raw.isdigit():
        return int(raw)
    return None


def _render_faltas_hoje_slot_inner(
    request: HttpRequest,
    empresa_ativa,
    edit_pk: Optional[int] = None,
) -> HttpResponse:
    if edit_pk is None:
        edit_pk = _parse_edit_pk(request, post=False)
    return render(
        request,
        'apontamento/partials/faltas_hoje_slot_inner.html',
        {
            'faltas_hoje': _faltas_registradas_hoje_queryset(request, empresa_ativa),
            'edit_pk': edit_pk,
            **_ctx_status_apontamento_mobile(request),
        },
    )


def _render_observacoes_hoje_slot_inner(
    request: HttpRequest,
    empresa_ativa,
    edit_pk: Optional[int] = None,
) -> HttpResponse:
    if edit_pk is None:
        edit_pk = _parse_edit_pk(request, post=False)
    return render(
        request,
        'apontamento/partials/observacoes_hoje_slot_inner.html',
        {
            'observacoes_hoje': _observacoes_registradas_hoje_queryset(request, empresa_ativa),
            'edit_pk': edit_pk,
            **_ctx_status_apontamento_mobile(request),
        },
    )


def _pode_modulo_apontamento(request: HttpRequest) -> bool:
    return bool(
        request.user.is_superuser
        or getattr(request, 'usuario_admin_empresa', False)
        or getattr(request, 'usuario_apontador', False)
    )


def _faltas_registradas_hoje_queryset(request: HttpRequest, empresa_ativa):
    hoje = timezone.localdate()
    return (
        ApontamentoFalta.objects.filter(
            empresa=empresa_ativa,
            registrado_por=request.user,
            criado_em__date=hoje,
        )
        .select_related('funcionario', 'funcionario__local_trabalho', 'status_alterado_por')
        .order_by('-criado_em')
    )


def _observacoes_registradas_hoje_queryset(request: HttpRequest, empresa_ativa):
    hoje = timezone.localdate()
    return (
        ApontamentoObservacaoLocal.objects.filter(
            empresa=empresa_ativa,
            registrado_por=request.user,
            criado_em__date=hoje,
        )
        .select_related('local', 'status_alterado_por')
        .order_by('-criado_em')
    )


def _get_observacao_editavel_hoje(
    request: HttpRequest, empresa_ativa, pk: int
) -> ApontamentoObservacaoLocal:
    hoje = timezone.localdate()
    return get_object_or_404(
        ApontamentoObservacaoLocal.objects.filter(criado_em__date=hoje),
        pk=pk,
        empresa=empresa_ativa,
        registrado_por=request.user,
    )


def _get_falta_editavel_hoje(request: HttpRequest, empresa_ativa, pk: int) -> ApontamentoFalta:
    """Falta desta empresa, registrada por mim hoje (criação no dia)."""
    hoje = timezone.localdate()
    return get_object_or_404(
        ApontamentoFalta.objects.filter(criado_em__date=hoje),
        pk=pk,
        empresa=empresa_ativa,
        registrado_por=request.user,
    )


def require_apontamento(view_func):
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not _pode_modulo_apontamento(request):
            messages.error(
                request,
                'Você não tem permissão para acessar o módulo Apontamento.',
            )
            empresa = getattr(request, 'empresa_ativa', None)
            if empresa:
                return redirect('dashboard_home', empresa_id=empresa.pk)
            return redirect('selecionar_empresa')

        return view_func(request, *args, **kwargs)

    return wrapper


@require_apontamento
def home(request: HttpRequest) -> HttpResponse:
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para continuar.',
    )
    if redirect_response:
        return redirect_response

    return render(
        request,
        'apontamento/home.html',
        {},
    )


@require_apontamento
def falta_nova(request: HttpRequest) -> HttpResponse:
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para continuar.',
    )
    if redirect_response:
        return redirect_response

    if request.method == 'POST':
        form = ApontamentoFaltaForm(
            request.POST,
            empresa_ativa=empresa_ativa,
        )
        if form.is_valid():
            obj: ApontamentoFalta = form.save(commit=False)
            obj.empresa = empresa_ativa
            obj.registrado_por = request.user
            obj.save()
            messages.success(request, 'Falta registrada para análise do RH.')
            return redirect('apontamento:falta_nova', empresa_id=empresa_ativa.pk)
    else:
        form = ApontamentoFaltaForm(empresa_ativa=empresa_ativa)

    faltas_hoje = _faltas_registradas_hoje_queryset(request, empresa_ativa)

    ctx = {
        'form': form,
        'faltas_hoje': faltas_hoje,
        'modo_edicao': False,
        'edit_pk': None,
    }
    ctx.update(_ctx_status_apontamento_mobile(request))
    return render(request, 'apontamento/falta_form.html', ctx)


@require_apontamento
def falta_editar(request: HttpRequest, pk: int) -> HttpResponse:
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para continuar.',
    )
    if redirect_response:
        return redirect_response

    falta = _get_falta_editavel_hoje(request, empresa_ativa, pk)

    if request.method == 'POST':
        form = ApontamentoFaltaForm(
            request.POST,
            empresa_ativa=empresa_ativa,
            instance=falta,
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Falta atualizada.')
            return redirect('apontamento:falta_nova', empresa_id=empresa_ativa.pk)
    else:
        form = ApontamentoFaltaForm(
            empresa_ativa=empresa_ativa,
            instance=falta,
        )

    faltas_hoje = _faltas_registradas_hoje_queryset(request, empresa_ativa)

    ctx = {
        'form': form,
        'faltas_hoje': faltas_hoje,
        'modo_edicao': True,
        'falta_edicao': falta,
        'edit_pk': falta.pk,
    }
    ctx.update(_ctx_status_apontamento_mobile(request))
    return render(request, 'apontamento/falta_form.html', ctx)


@require_apontamento
@require_POST
def falta_excluir(request: HttpRequest, pk: int) -> HttpResponse:
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para continuar.',
    )
    if redirect_response:
        return redirect_response

    falta = _get_falta_editavel_hoje(request, empresa_ativa, pk)
    falta.delete()
    messages.success(request, 'Falta excluída.')
    return redirect('apontamento:falta_nova', empresa_id=empresa_ativa.pk)


@require_apontamento
def observacao_nova(request: HttpRequest) -> HttpResponse:
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para continuar.',
    )
    if redirect_response:
        return redirect_response

    tem_locais = Local.objects.filter(empresa=empresa_ativa).exists()

    if request.method == 'POST' and not tem_locais:
        messages.error(
            request,
            'Não há locais cadastrados para esta empresa.',
        )
        return redirect('apontamento:observacao_nova', empresa_id=empresa_ativa.pk)

    if request.method == 'POST':
        form = ApontamentoObservacaoLocalForm(
            request.POST,
            empresa_ativa=empresa_ativa,
        )
        if form.is_valid():
            obj: ApontamentoObservacaoLocal = form.save(commit=False)
            obj.empresa = empresa_ativa
            obj.registrado_por = request.user
            obj.save()
            messages.success(request, 'Observação registrada.')
            return redirect('apontamento:observacao_nova', empresa_id=empresa_ativa.pk)
    else:
        form = ApontamentoObservacaoLocalForm(empresa_ativa=empresa_ativa)

    observacoes_hoje = _observacoes_registradas_hoje_queryset(request, empresa_ativa)

    ctx = {
        'form': form,
        'tem_locais': tem_locais,
        'observacoes_hoje': observacoes_hoje,
        'modo_edicao': False,
        'edit_pk': None,
    }
    ctx.update(_ctx_status_apontamento_mobile(request))
    return render(request, 'apontamento/observacao_form.html', ctx)


@require_apontamento
def observacao_editar(request: HttpRequest, pk: int) -> HttpResponse:
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para continuar.',
    )
    if redirect_response:
        return redirect_response

    obs = _get_observacao_editavel_hoje(request, empresa_ativa, pk)
    tem_locais = Local.objects.filter(empresa=empresa_ativa).exists()

    if not tem_locais:
        messages.error(
            request,
            'Não há locais cadastrados. Não é possível editar observações.',
        )
        return redirect('apontamento:observacao_nova', empresa_id=empresa_ativa.pk)

    if request.method == 'POST':
        form = ApontamentoObservacaoLocalForm(
            request.POST,
            empresa_ativa=empresa_ativa,
            instance=obs,
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Observação atualizada.')
            return redirect('apontamento:observacao_nova', empresa_id=empresa_ativa.pk)
    else:
        form = ApontamentoObservacaoLocalForm(
            empresa_ativa=empresa_ativa,
            instance=obs,
        )

    observacoes_hoje = _observacoes_registradas_hoje_queryset(request, empresa_ativa)

    ctx = {
        'form': form,
        'tem_locais': tem_locais,
        'observacoes_hoje': observacoes_hoje,
        'modo_edicao': True,
        'observacao_edicao': obs,
        'edit_pk': obs.pk,
    }
    ctx.update(_ctx_status_apontamento_mobile(request))
    return render(request, 'apontamento/observacao_form.html', ctx)


@require_apontamento
@require_POST
def observacao_excluir(request: HttpRequest, pk: int) -> HttpResponse:
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para continuar.',
    )
    if redirect_response:
        return redirect_response

    obs = _get_observacao_editavel_hoje(request, empresa_ativa, pk)
    obs.delete()
    messages.success(request, 'Observação excluída.')
    return redirect('apontamento:observacao_nova', empresa_id=empresa_ativa.pk)


@require_apontamento
def busca_funcionarios(request: HttpRequest) -> HttpResponse:
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para continuar.',
    )
    if redirect_response:
        return redirect_response

    q = (request.GET.get('q') or '').strip()
    muito_curto = len(q) < 2
    resultados = []

    if not muito_curto:
        qs = (
            Funcionario.objects.filter(empresa=empresa_ativa)
            .exclude(situacao_atual__in=['demitido', 'inativo'])
            .filter(
                Q(nome__icontains=q)
                | Q(cpf__icontains=q)
                | Q(matricula__icontains=q)
                | Q(pis__icontains=q)
            )
            .select_related('cargo', 'lotacao')
            .order_by('nome')
        )
        resultados = list(qs[:25])

    return render(
        request,
        'apontamento/partials/busca_funcionarios.html',
        {'resultados': resultados, 'q': q, 'muito_curto': muito_curto},
    )


@require_apontamento
def faltas_hoje_fragment(request: HttpRequest) -> HttpResponse:
    """HTMX: lista «Suas faltas hoje» (polling ou uso interno)."""
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para continuar.',
    )
    if redirect_response:
        return redirect_response

    return _render_faltas_hoje_slot_inner(request, empresa_ativa)


@require_apontamento
def observacoes_hoje_fragment(request: HttpRequest) -> HttpResponse:
    """HTMX: lista «Suas anotações hoje» (polling ou uso interno)."""
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para continuar.',
    )
    if redirect_response:
        return redirect_response

    return _render_observacoes_hoje_slot_inner(request, empresa_ativa)


@require_POST
def falta_alterar_status(request: HttpRequest, pk: int) -> HttpResponse:
    """RH: altera status da falta de apontamento (dashboard ou tela mobile)."""
    from rh.views.dashboard import render_dashboard_apontamento_partial

    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para continuar.',
    )
    if redirect_response:
        return redirect_response

    if not usuario_rh_pode_gerir_status_apontamento(request):
        messages.error(request, 'Sem permissão para alterar o status.')
        return redirect('rh:dashboard_rh', empresa_id=empresa_ativa.pk)

    obj = get_object_or_404(
        ApontamentoFalta,
        pk=pk,
        empresa=empresa_ativa,
    )
    raw = (request.POST.get('status') or '').strip()
    valid = {c[0] for c in StatusApontamento.choices}
    retorno = (request.POST.get('retorno') or '').strip()
    if raw not in valid:
        messages.error(request, 'Status inválido.')
    elif raw != obj.status:
        obj.status = raw
        obj.status_alterado_por = request.user
        obj.status_alterado_em = timezone.now()
        obj.save(
            update_fields=[
                'status',
                'atualizado_em',
                'status_alterado_por',
                'status_alterado_em',
            ]
        )
        messages.success(request, 'Status da falta atualizado.')

    if retorno == 'mobile_falta':
        if _is_htmx(request):
            edit_pk = _parse_edit_pk(request, post=True)
            return _render_faltas_hoje_slot_inner(request, empresa_ativa, edit_pk=edit_pk)
        return redirect('apontamento:falta_nova', empresa_id=empresa_ativa.pk)
    return render_dashboard_apontamento_partial(request)


@require_POST
def observacao_alterar_status(request: HttpRequest, pk: int) -> HttpResponse:
    """RH: altera status da observação de local (dashboard ou tela mobile)."""
    from rh.views.dashboard import render_dashboard_apontamento_partial

    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para continuar.',
    )
    if redirect_response:
        return redirect_response

    if not usuario_rh_pode_gerir_status_apontamento(request):
        messages.error(request, 'Sem permissão para alterar o status.')
        return redirect('rh:dashboard_rh', empresa_id=empresa_ativa.pk)

    obj = get_object_or_404(
        ApontamentoObservacaoLocal,
        pk=pk,
        empresa=empresa_ativa,
    )
    raw = (request.POST.get('status') or '').strip()
    valid = {c[0] for c in StatusApontamento.choices}
    retorno = (request.POST.get('retorno') or '').strip()
    if raw not in valid:
        messages.error(request, 'Status inválido.')
    elif raw != obj.status:
        obj.status = raw
        obj.status_alterado_por = request.user
        obj.status_alterado_em = timezone.now()
        obj.save(
            update_fields=[
                'status',
                'atualizado_em',
                'status_alterado_por',
                'status_alterado_em',
            ]
        )
        messages.success(request, 'Status da observação atualizado.')

    if retorno == 'mobile_obs':
        if _is_htmx(request):
            edit_pk = _parse_edit_pk(request, post=True)
            return _render_observacoes_hoje_slot_inner(request, empresa_ativa, edit_pk=edit_pk)
        return redirect('apontamento:observacao_nova', empresa_id=empresa_ativa.pk)
    return render_dashboard_apontamento_partial(request)
