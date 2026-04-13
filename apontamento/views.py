import calendar
from datetime import date, timedelta
from functools import wraps
from typing import Optional, Tuple

from django.contrib import messages
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from local.models import Local
from auditoria.registry import audit_apontamento
from rh.models import Funcionario
from rh.views.base import _empresa_ativa_or_redirect

from .forms import ApontamentoFaltaForm, ApontamentoObservacaoLocalForm
from .models import (
    ApontamentoFalta,
    ApontamentoObservacaoFoto,
    ApontamentoObservacaoLocal,
    StatusApontamento,
)
from .permissions import (
    usuario_apontamento_ve_registros_de_todos,
    usuario_rh_pode_gerir_status_apontamento,
)


def _ctx_status_apontamento_mobile(request: HttpRequest) -> dict:
    return {
        'pode_gerir_status_apontamento': usuario_rh_pode_gerir_status_apontamento(
            request
        ),
        'status_apontamento_choices': StatusApontamento.choices,
    }


def _ctx_apontamento_listas(request: HttpRequest) -> dict:
    ctx = _ctx_status_apontamento_mobile(request)
    ctx['apont_ve_todos_registros'] = usuario_apontamento_ve_registros_de_todos(
        request
    )
    return ctx


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
            **_ctx_apontamento_listas(request),
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
            'observacoes_hoje': _observacoes_registradas_hoje_queryset(
                request, empresa_ativa
            ),
            'edit_pk': edit_pk,
            **_ctx_apontamento_listas(request),
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
    filtro = dict(empresa=empresa_ativa, criado_em__date=hoje)
    if not usuario_apontamento_ve_registros_de_todos(request):
        filtro['registrado_por'] = request.user
    return (
        ApontamentoFalta.objects.filter(**filtro)
        .select_related(
            'funcionario',
            'funcionario__cargo',
            'funcionario__local_trabalho',
            'status_alterado_por',
            'registrado_por',
        )
        .order_by('-criado_em')
    )


def _observacoes_registradas_hoje_queryset(request: HttpRequest, empresa_ativa):
    hoje = timezone.localdate()
    filtro = dict(empresa=empresa_ativa, criado_em__date=hoje)
    if not usuario_apontamento_ve_registros_de_todos(request):
        filtro['registrado_por'] = request.user
    return (
        ApontamentoObservacaoLocal.objects.filter(**filtro)
        .select_related('local', 'status_alterado_por', 'registrado_por')
        .prefetch_related('fotos')
        .order_by('-criado_em')
    )


def _intervalo_mes_corrente_local() -> Tuple[date, date]:
    hoje = timezone.localdate()
    inicio = hoje.replace(day=1)
    _, ultimo_dia = calendar.monthrange(hoje.year, hoje.month)
    fim = hoje.replace(day=ultimo_dia)
    return inicio, fim


def _nome_exibicao_apontador(request: HttpRequest) -> str:
    u = request.user
    nome = (u.get_full_name() or u.first_name or u.username or '').strip()
    return nome or 'apontador'


def _faltas_mes_queryset(request: HttpRequest, empresa_ativa):
    inicio, fim = _intervalo_mes_corrente_local()
    filtro = dict(
        empresa=empresa_ativa,
        criado_em__date__gte=inicio,
        criado_em__date__lte=fim,
    )
    if not usuario_apontamento_ve_registros_de_todos(request):
        filtro['registrado_por'] = request.user
    return (
        ApontamentoFalta.objects.filter(**filtro)
        .select_related(
            'funcionario',
            'funcionario__cargo',
            'funcionario__local_trabalho',
            'registrado_por',
        )
        .order_by('-criado_em')
    )


def _observacoes_mes_queryset(request: HttpRequest, empresa_ativa):
    inicio, fim = _intervalo_mes_corrente_local()
    filtro = dict(
        empresa=empresa_ativa,
        criado_em__date__gte=inicio,
        criado_em__date__lte=fim,
    )
    if not usuario_apontamento_ve_registros_de_todos(request):
        filtro['registrado_por'] = request.user
    return (
        ApontamentoObservacaoLocal.objects.filter(**filtro)
        .select_related('local', 'registrado_por')
        .prefetch_related('fotos')
        .order_by('-criado_em')
    )


def _salvar_fotos_observacao_novas(
    observacao: ApontamentoObservacaoLocal,
    files: list,
) -> None:
    for f in files:
        ApontamentoObservacaoFoto.objects.create(observacao=observacao, imagem=f)


def _get_observacao_editavel_hoje(
    request: HttpRequest, empresa_ativa, pk: int
) -> ApontamentoObservacaoLocal:
    hoje = timezone.localdate()
    return get_object_or_404(
        ApontamentoObservacaoLocal.objects.filter(
            criado_em__date=hoje,
        )
        .select_related('local')
        .prefetch_related('fotos'),
        pk=pk,
        empresa=empresa_ativa,
        registrado_por=request.user,
    )


def _get_falta_editavel_hoje(request: HttpRequest, empresa_ativa, pk: int) -> ApontamentoFalta:
    """Falta desta empresa, registrada por mim hoje (criação no dia)."""
    hoje = timezone.localdate()
    return get_object_or_404(
        ApontamentoFalta.objects.filter(criado_em__date=hoje).select_related(
            'funcionario',
        ),
        pk=pk,
        empresa=empresa_ativa,
        registrado_por=request.user,
    )


_MSG_APONT_FALTA_ARQUIVADA = (
    'Faltas marcadas como Arquivado pelo RH não podem ser editadas nem excluídas.'
)
_MSG_APONT_OBS_ARQUIVADA = (
    'Anotações marcadas como Arquivado pelo RH não podem ser editadas nem excluídas.'
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

    qs_faltas_mes = _faltas_mes_queryset(request, empresa_ativa)
    qs_obs_mes = _observacoes_mes_queryset(request, empresa_ativa)

    return render(
        request,
        'apontamento/home.html',
        {
            'apont_nome': _nome_exibicao_apontador(request),
            'apont_hoje': timezone.localdate(),
            'apont_faltas_mes_count': qs_faltas_mes.count(),
            'apont_ultima_falta_mes': qs_faltas_mes.first(),
            'apont_observacoes_mes_count': qs_obs_mes.count(),
            'apont_ultima_observacao_mes': qs_obs_mes.first(),
            'apont_ve_todos_registros': usuario_apontamento_ve_registros_de_todos(
                request
            ),
        },
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
            audit_apontamento(
                request,
                acao='create',
                resumo=(
                    f'Apontamento: inclusão de falta — {obj.funcionario.nome} '
                    f'(id {obj.pk}, data da falta {obj.data.strftime("%d/%m/%Y")})'
                ),
                detalhes={
                    'tipo': 'falta',
                    'pk': obj.pk,
                    'funcionario_id': obj.funcionario_id,
                    'funcionario_nome': obj.funcionario.nome,
                    'data': str(obj.data),
                    'status': obj.status,
                },
            )
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
    ctx.update(_ctx_apontamento_listas(request))
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
    if falta.status == StatusApontamento.ARQUIVADO:
        messages.error(request, _MSG_APONT_FALTA_ARQUIVADA)
        return redirect('apontamento:falta_nova', empresa_id=empresa_ativa.pk)

    if request.method == 'POST':
        form = ApontamentoFaltaForm(
            request.POST,
            empresa_ativa=empresa_ativa,
            instance=falta,
        )
        if form.is_valid():
            falta_atualizada = form.save()
            audit_apontamento(
                request,
                acao='update',
                resumo=(
                    f'Apontamento: alteração de falta — '
                    f'{falta_atualizada.funcionario.nome} '
                    f'(id {falta_atualizada.pk}, '
                    f'data da falta {falta_atualizada.data.strftime("%d/%m/%Y")})'
                ),
                detalhes={
                    'tipo': 'falta',
                    'pk': falta_atualizada.pk,
                    'funcionario_id': falta_atualizada.funcionario_id,
                    'funcionario_nome': falta_atualizada.funcionario.nome,
                    'data': str(falta_atualizada.data),
                    'status': falta_atualizada.status,
                },
            )
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
    ctx.update(_ctx_apontamento_listas(request))
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
    if falta.status == StatusApontamento.ARQUIVADO:
        messages.error(request, _MSG_APONT_FALTA_ARQUIVADA)
        return redirect('apontamento:falta_nova', empresa_id=empresa_ativa.pk)
    detalhes_excl = {
        'tipo': 'falta',
        'pk': falta.pk,
        'funcionario_id': falta.funcionario_id,
        'funcionario_nome': falta.funcionario.nome,
        'data': str(falta.data),
        'status': falta.status,
    }
    resumo_excl = (
        f'Apontamento: exclusão de falta — {falta.funcionario.nome} '
        f'(id {falta.pk}, data da falta {falta.data.strftime("%d/%m/%Y")})'
    )
    falta.delete()
    audit_apontamento(
        request,
        acao='delete',
        resumo=resumo_excl,
        detalhes=detalhes_excl,
    )
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
            request.FILES,
            empresa_ativa=empresa_ativa,
        )
        if form.is_valid():
            obj: ApontamentoObservacaoLocal = form.save(commit=False)
            obj.empresa = empresa_ativa
            obj.registrado_por = request.user
            obj.save()
            _salvar_fotos_observacao_novas(obj, form.fotos_novas_para_salvar())
            audit_apontamento(
                request,
                acao='create',
                resumo=(
                    f'Apontamento: inclusão de anotação — {obj.local.nome} '
                    f'({obj.data.strftime("%d/%m/%Y")})'
                ),
                detalhes={
                    'tipo': 'anotacao',
                    'pk': obj.pk,
                    'local_id': obj.local_id,
                    'local_nome': obj.local.nome,
                    'data': str(obj.data),
                    'status': obj.status,
                },
            )
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
    ctx.update(_ctx_apontamento_listas(request))
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
    if obs.status == StatusApontamento.ARQUIVADO:
        messages.error(request, _MSG_APONT_OBS_ARQUIVADA)
        return redirect('apontamento:observacao_nova', empresa_id=empresa_ativa.pk)

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
            request.FILES,
            empresa_ativa=empresa_ativa,
            instance=obs,
        )
        if form.is_valid():
            obs_atual = form.save()
            _salvar_fotos_observacao_novas(obs_atual, form.fotos_novas_para_salvar())
            audit_apontamento(
                request,
                acao='update',
                resumo=(
                    f'Apontamento: alteração de anotação — '
                    f'{obs_atual.local.nome} (id {obs_atual.pk})'
                ),
                detalhes={
                    'tipo': 'anotacao',
                    'pk': obs_atual.pk,
                    'local_id': obs_atual.local_id,
                    'local_nome': obs_atual.local.nome,
                    'data': str(obs_atual.data),
                    'status': obs_atual.status,
                },
            )
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
    ctx.update(_ctx_apontamento_listas(request))
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
    if obs.status == StatusApontamento.ARQUIVADO:
        messages.error(request, _MSG_APONT_OBS_ARQUIVADA)
        return redirect('apontamento:observacao_nova', empresa_id=empresa_ativa.pk)
    detalhes_obs_excl = {
        'tipo': 'anotacao',
        'pk': obs.pk,
        'local_id': obs.local_id,
        'local_nome': obs.local.nome,
        'data': str(obs.data),
        'status': obs.status,
    }
    resumo_obs_excl = (
        f'Apontamento: exclusão de anotação — {obs.local.nome} (id {obs.pk})'
    )
    obs.delete()
    audit_apontamento(
        request,
        acao='delete',
        resumo=resumo_obs_excl,
        detalhes=detalhes_obs_excl,
    )
    messages.success(request, 'Observação excluída.')
    return redirect('apontamento:observacao_nova', empresa_id=empresa_ativa.pk)


@require_apontamento
@require_POST
def observacao_foto_excluir(
    request: HttpRequest, observacao_pk: int, foto_pk: int
) -> HttpResponse:
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para continuar.',
    )
    if redirect_response:
        return redirect_response

    obs = _get_observacao_editavel_hoje(request, empresa_ativa, observacao_pk)
    if obs.status == StatusApontamento.ARQUIVADO:
        messages.error(request, _MSG_APONT_OBS_ARQUIVADA)
        return redirect('apontamento:observacao_nova', empresa_id=empresa_ativa.pk)

    foto = get_object_or_404(
        ApontamentoObservacaoFoto.objects.filter(observacao=obs),
        pk=foto_pk,
    )
    if foto.imagem and getattr(foto.imagem, 'name', ''):
        try:
            foto.imagem.delete(save=False)
        except OSError:
            pass
    foto.delete()
    audit_apontamento(
        request,
        acao='delete',
        resumo=(
            f'Apontamento: exclusão de foto de anotação — '
            f'{obs.local.nome} (obs. {obs.pk}, foto {foto_pk})'
        ),
        detalhes={
            'tipo': 'anotacao_foto',
            'observacao_pk': obs.pk,
            'foto_pk': foto_pk,
            'local_nome': obs.local.nome,
        },
    )
    messages.success(request, 'Foto excluída.')
    return redirect(
        'apontamento:observacao_editar',
        empresa_id=empresa_ativa.pk,
        pk=observacao_pk,
    )


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


_PERIODO_APONTAMENTO_ANTERIORES_MAX_DIAS = 366


def _parse_periodo_apontamento_anteriores(request: HttpRequest) -> tuple[date, date]:
    """Intervalo [de, ate] a partir de GET (de/ate ISO), com limites e mensagens como nas telas de histórico."""
    hoje = timezone.localdate()
    default_de = hoje - timedelta(days=30)
    raw_de = (request.GET.get('de') or '').strip()
    raw_ate = (request.GET.get('ate') or '').strip()
    try:
        data_de = date.fromisoformat(raw_de) if raw_de else default_de
        data_ate = date.fromisoformat(raw_ate) if raw_ate else hoje
    except ValueError:
        messages.error(request, 'Informe datas válidas no período.')
        data_de, data_ate = default_de, hoje

    if data_de > data_ate:
        data_de, data_ate = data_ate, data_de

    if (data_ate - data_de).days > _PERIODO_APONTAMENTO_ANTERIORES_MAX_DIAS:
        messages.warning(
            request,
            f'O período máximo de busca é de {_PERIODO_APONTAMENTO_ANTERIORES_MAX_DIAS} dias. '
            'A data final foi ajustada.',
        )
        data_ate = data_de + timedelta(days=_PERIODO_APONTAMENTO_ANTERIORES_MAX_DIAS)

    return data_de, data_ate


@require_apontamento
def faltas_anteriores(request: HttpRequest) -> HttpResponse:
    """Lista faltas de apontamento do utilizador, filtradas pela data da falta."""
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para continuar.',
    )
    if redirect_response:
        return redirect_response

    data_de, data_ate = _parse_periodo_apontamento_anteriores(request)

    filtro = dict(
        empresa=empresa_ativa,
        data__gte=data_de,
        data__lte=data_ate,
    )
    if not usuario_apontamento_ve_registros_de_todos(request):
        filtro['registrado_por'] = request.user

    faltas = (
        ApontamentoFalta.objects.filter(**filtro)
        .select_related(
            'funcionario',
            'funcionario__cargo',
            'funcionario__local_trabalho',
            'status_alterado_por',
            'registrado_por',
        )
        .order_by('-data', '-criado_em')
    )

    return render(
        request,
        'apontamento/faltas_anteriores.html',
        {
            'faltas': faltas,
            'periodo_de': data_de,
            'periodo_ate': data_ate,
            'apont_ve_todos_registros': usuario_apontamento_ve_registros_de_todos(
                request
            ),
        },
    )


@require_apontamento
def observacoes_anteriores(request: HttpRequest) -> HttpResponse:
    """Lista anotações de local do utilizador, filtradas pela data do registro."""
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para continuar.',
    )
    if redirect_response:
        return redirect_response

    data_de, data_ate = _parse_periodo_apontamento_anteriores(request)

    filtro = dict(
        empresa=empresa_ativa,
        data__gte=data_de,
        data__lte=data_ate,
    )
    if not usuario_apontamento_ve_registros_de_todos(request):
        filtro['registrado_por'] = request.user

    observacoes = (
        ApontamentoObservacaoLocal.objects.filter(**filtro)
        .select_related('local', 'status_alterado_por', 'registrado_por')
        .prefetch_related('fotos')
        .order_by('-data', '-criado_em')
    )

    return render(
        request,
        'apontamento/observacoes_anteriores.html',
        {
            'observacoes': observacoes,
            'periodo_de': data_de,
            'periodo_ate': data_ate,
            'apont_ve_todos_registros': usuario_apontamento_ve_registros_de_todos(
                request
            ),
        },
    )


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
        ApontamentoFalta.objects.select_related('funcionario'),
        pk=pk,
        empresa=empresa_ativa,
    )
    raw = (request.POST.get('status') or '').strip()
    valid = {c[0] for c in StatusApontamento.choices}
    retorno = (request.POST.get('retorno') or '').strip()
    if raw not in valid:
        messages.error(request, 'Status inválido.')
    elif raw != obj.status:
        old_status = obj.status
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
        audit_apontamento(
            request,
            acao='update',
            resumo=(
                f'Apontamento: alteração de status (RH) — falta '
                f'{obj.funcionario.nome} '
                f'(id {obj.pk}, data da falta {obj.data.strftime("%d/%m/%Y")})'
            ),
            detalhes={
                'tipo': 'falta_status',
                'pk': obj.pk,
                'funcionario_nome': obj.funcionario.nome,
                'data_falta': str(obj.data),
                'status_anterior': old_status,
                'status_novo': raw,
            },
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
        ApontamentoObservacaoLocal.objects.select_related('local'),
        pk=pk,
        empresa=empresa_ativa,
    )
    raw = (request.POST.get('status') or '').strip()
    valid = {c[0] for c in StatusApontamento.choices}
    retorno = (request.POST.get('retorno') or '').strip()
    if raw not in valid:
        messages.error(request, 'Status inválido.')
    elif raw != obj.status:
        old_status = obj.status
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
        audit_apontamento(
            request,
            acao='update',
            resumo=(
                f'Apontamento: alteração de status (RH) — anotação '
                f'{obj.local.nome} (id {obj.pk})'
            ),
            detalhes={
                'tipo': 'anotacao_status',
                'pk': obj.pk,
                'local_nome': obj.local.nome,
                'status_anterior': old_status,
                'status_novo': raw,
            },
        )
        messages.success(request, 'Status da observação atualizado.')

    if retorno == 'mobile_obs':
        if _is_htmx(request):
            edit_pk = _parse_edit_pk(request, post=True)
            return _render_observacoes_hoje_slot_inner(request, empresa_ativa, edit_pk=edit_pk)
        return redirect('apontamento:observacao_nova', empresa_id=empresa_ativa.pk)
    return render_dashboard_apontamento_partial(request)
