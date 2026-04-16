from __future__ import annotations

import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods

from auditoria.registry import registrar_auditoria
from core.urlutils import redirect_empresa, reverse_empresa

from .cautela_forms import (
    CautelaForm,
    CautelaStaffEditForm,
    EntregaCautelaDevolucaoForm,
)
from .models import (
    Cautela,
    Entrega_Cautela,
    Ferramenta,
    MotivoDevolucaoCautela,
    RascunhoNovaCautela,
    SituacaoFerramentasPosDevolucao,
)


def _empresa(request):
    return getattr(request, 'empresa_ativa', None)


def _is_htmx(request):
    v = request.headers.get('HX-Request')
    if v is None:
        v = request.META.get('HTTP_HX_REQUEST')
    return str(v).lower() == 'true'


def _hx_redirect(request, viewname: str, *, args=None, kwargs=None):
    resp = HttpResponse(status=200)
    resp['HX-Redirect'] = reverse_empresa(
        request, viewname, args=args, kwargs=kwargs
    )
    return resp


def _parse_ferramentas_devolucao_ids(request) -> list[int]:
    ids: list[int] = []
    for r in request.POST.getlist('ferramentas_devolvidas'):
        try:
            pid = int(str(r).strip())
        except ValueError:
            continue
        if pid > 0 and pid not in ids:
            ids.append(pid)
    return ids


def _devolucao_catalogos_prontos(empresa) -> bool:
    return (
        MotivoDevolucaoCautela.objects.filter(empresa=empresa, ativo=True).exists()
        and SituacaoFerramentasPosDevolucao.objects.filter(
            empresa=empresa, ativo=True
        ).exists()
    )


_RASCUNHO_FORM_KEYS = frozenset(
    {
        'funcionario_id',
        'funcionario_label',
        'local_id',
        'local_label',
        'obra_id',
        'data_inicio',
        'data_fim',
        'observacoes',
    },
)
_RASCUNHO_ITEM_STR_MAX = 500
_RASCUNHO_OBS_MAX = 4000
_RASCUNHO_MAX_ITEMS = 500
_RASCUNHO_BODY_MAX = 600_000


def _sanitizar_rascunho_nova_cautela(payload: object) -> dict:
    if not isinstance(payload, dict):
        return {'form': {}, 'items': []}
    out_form: dict[str, str] = {}
    raw_form = payload.get('form')
    if isinstance(raw_form, dict):
        for k in _RASCUNHO_FORM_KEYS:
            v = raw_form.get(k, '')
            if v is None:
                v = ''
            lim = _RASCUNHO_OBS_MAX if k == 'observacoes' else _RASCUNHO_ITEM_STR_MAX
            out_form[k] = str(v)[:lim]
    items: list[dict] = []
    raw_items = payload.get('items')
    if isinstance(raw_items, list):
        for it in raw_items[:_RASCUNHO_MAX_ITEMS]:
            if not isinstance(it, dict):
                continue
            try:
                fid = int(it.get('id'))
            except (TypeError, ValueError):
                continue
            if fid <= 0:
                continue
            du = str(it.get('detail_url', '') or '')[:800]
            items.append(
                {
                    'id': fid,
                    'desc': str(it.get('desc', '') or '')[:_RASCUNHO_ITEM_STR_MAX],
                    'marca': str(it.get('marca', '') or '')[:_RASCUNHO_ITEM_STR_MAX],
                    'cat': str(it.get('cat', '') or '')[:_RASCUNHO_ITEM_STR_MAX],
                    'code': str(it.get('code', '') or '')[:_RASCUNHO_ITEM_STR_MAX],
                    'cor': str(it.get('cor', '') or '')[:_RASCUNHO_ITEM_STR_MAX],
                    'tamanho': str(it.get('tamanho', '') or '')[:_RASCUNHO_ITEM_STR_MAX],
                    'detail_url': du,
                }
            )
    return {'form': out_form, 'items': items}


def _excluir_rascunho_nova_cautela(empresa, user) -> None:
    RascunhoNovaCautela.objects.filter(empresa=empresa, usuario=user).delete()


def _obter_rascunho_nova_cautela(empresa, user):
    return (
        RascunhoNovaCautela.objects.filter(empresa=empresa, usuario=user)
        .only('dados')
        .first()
    )


def _rascunho_nova_cautela_de_post(request, empresa) -> dict | None:
    """Reidrata o JS após POST com erro (lista de ferramentas só existe no cliente)."""
    p = request.POST
    raw_ids = p.getlist('ferramentas_ids')
    ids: list[int] = []
    for r in raw_ids:
        try:
            rid = int(str(r).strip())
        except Exception:
            continue
        if rid not in ids:
            ids.append(rid)

    form_vals = {
        'funcionario_id': (p.get('funcionario') or '').strip(),
        'funcionario_label': (p.get('q_solicitante') or '').strip(),
        'local_id': (p.get('local') or '').strip(),
        'local_label': (p.get('q_local') or '').strip(),
        'obra_id': (p.get('obra') or '').strip(),
        'data_inicio': (p.get('data_inicio_cautela') or '').strip(),
        'data_fim': (p.get('data_fim') or '').strip(),
        'observacoes': (p.get('observacoes') or '').strip(),
    }
    has_form = any(v for v in form_vals.values())
    if not ids and not has_form:
        return None

    items: list[dict] = []
    if ids:
        ferrs = {
            f.pk: f
            for f in Ferramenta.objects.filter(
                empresa=empresa, pk__in=ids
            ).select_related('categoria')
        }
        for rid in ids:
            f = ferrs.get(rid)
            if not f:
                continue
            items.append(
                {
                    'id': rid,
                    'desc': f.descricao,
                    'marca': f.marca or '',
                    'cat': f.categoria.nome if f.categoria_id else '',
                    'code': f.codigo_numeracao or '',
                    'cor': f.cor or '',
                    'tamanho': f.tamanho or '',
                    'detail_url': reverse_empresa(
                        request,
                        'estoque:detalhes_ferramenta',
                        kwargs={'pk': f.pk},
                    ),
                }
            )

    return {'form': form_vals, 'items': items}


@login_required
def cautela_ferramentas(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    cautelas = (
        Cautela.objects.filter(empresa=empresa)
        .select_related('funcionario', 'almoxarife', 'local', 'obra')
        .prefetch_related(
            Prefetch(
                'entregas',
                queryset=Entrega_Cautela.objects.order_by(
                    '-data_entrega', '-criado_em'
                ),
            ),
        )
        .annotate(quantidade_ferramentas=Count('ferramentas', distinct=True))
        .order_by('-criado_em')
    )

    return render(
        request,
        'estoque/ferramentas/cautela.html',
        {
            'page_title': 'Cautela de ferramentas',
            'cautelas': cautelas,
            'hoje': timezone.localdate(),
        },
    )


@login_required
def detalhe_cautela(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    cautela = get_object_or_404(
        Cautela.objects.select_related('funcionario', 'almoxarife', 'local', 'obra')
        .prefetch_related(
            Prefetch(
                'entregas',
                queryset=(
                    Entrega_Cautela.objects.select_related(
                        'motivo', 'situacao_ferramentas'
                    )
                    .prefetch_related(
                        Prefetch(
                            'ferramentas_devolvidas',
                            queryset=Ferramenta.objects.select_related(
                                'categoria'
                            ).order_by('descricao'),
                        ),
                    )
                    .order_by('-data_entrega', '-criado_em')
                ),
            ),
            Prefetch(
                'ferramentas',
                queryset=Ferramenta.objects.select_related('categoria').order_by(
                    'descricao'
                ),
            ),
        ),
        pk=pk,
        empresa=empresa,
    )
    pode_registrar_devolucao = (
        cautela.situacao != Cautela.Situacao.INATIVA
        and cautela.entrega != Cautela.Entrega.TOTAL
        and cautela.ferramentas.exists()
    )
    pode_adiar_cautela = cautela.situacao == Cautela.Situacao.ATIVA

    ferramentas_ativas_na_cautela = list(cautela.ferramentas.all())
    ativas_ids = {f.pk for f in ferramentas_ativas_na_cautela}
    entregues_por_pk: dict[int, Ferramenta] = {}
    for ent in cautela.entregas.all():
        for f in ent.ferramentas_devolvidas.all():
            entregues_por_pk[f.pk] = f
    ferramentas_entregues_na_cautela = sorted(
        (
            f
            for pk, f in entregues_por_pk.items()
            if pk not in ativas_ids
        ),
        key=lambda x: x.descricao.lower(),
    )
    total_ferramentas_listagem = len(ferramentas_ativas_na_cautela) + len(
        ferramentas_entregues_na_cautela
    )

    return render(
        request,
        'estoque/ferramentas/cautela_detalhe.html',
        {
            'page_title': f'Cautela #{cautela.pk}',
            'cautela': cautela,
            'hoje': timezone.localdate(),
            'pode_registrar_devolucao': pode_registrar_devolucao,
            'pode_adiar_cautela': pode_adiar_cautela,
            'staff_pode_gerir_cautela': request.user.is_staff,
            'ferramentas_ativas_na_cautela': ferramentas_ativas_na_cautela,
            'ferramentas_entregues_na_cautela': ferramentas_entregues_na_cautela,
            'total_ferramentas_listagem': total_ferramentas_listagem,
        },
    )


def _clamp_date_not_before(d, lo):
    return d if d >= lo else lo


@login_required
def modal_adiar_cautela(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    cautela = get_object_or_404(
        Cautela.objects.select_related('funcionario'),
        pk=pk,
        empresa=empresa,
    )

    if not _is_htmx(request):
        return redirect_empresa(
            request, 'estoque:cautela_detalhe', kwargs={'pk': pk}
        )

    post_url = reverse_empresa(
        request, 'estoque:modal_adiar_cautela', kwargs={'pk': cautela.pk}
    )
    hoje = timezone.localdate()
    inicio = cautela.data_inicio_cautela

    def _ctx(extra=None):
        ctx = {
            'cautela': cautela,
            'post_url': post_url,
            'adiar_bloqueada': cautela.situacao == Cautela.Situacao.INATIVA,
        }
        if extra:
            ctx.update(extra)
        return ctx

    if cautela.situacao == Cautela.Situacao.INATIVA:
        return render(
            request,
            'estoque/partials/cautela_adiar_modal.html',
            _ctx(),
        )

    base = cautela.data_fim or hoje
    if base < inicio:
        base = inicio
    sug7 = _clamp_date_not_before(base + timedelta(days=7), inicio)
    sug30 = _clamp_date_not_before(base + timedelta(days=30), inicio)
    data_fim_inicial_iso = cautela.data_fim.isoformat() if cautela.data_fim else ''

    if request.method == 'POST':
        raw = (request.POST.get('data_fim') or '').strip()
        if not raw:
            return render(
                request,
                'estoque/partials/cautela_adiar_modal.html',
                _ctx(
                    {
                        'data_fim_inicial_iso': data_fim_inicial_iso,
                        'data_inicio_iso': inicio.isoformat(),
                        'sugestao_7_iso': sug7.isoformat(),
                        'sugestao_30_iso': sug30.isoformat(),
                        'form_erro': 'Informe a nova data de previsão.',
                    }
                ),
            )
        nova = parse_date(raw)
        if nova is None:
            return render(
                request,
                'estoque/partials/cautela_adiar_modal.html',
                _ctx(
                    {
                        'data_fim_inicial_iso': '',
                        'data_inicio_iso': inicio.isoformat(),
                        'sugestao_7_iso': sug7.isoformat(),
                        'sugestao_30_iso': sug30.isoformat(),
                        'form_erro': 'Data inválida.',
                    }
                ),
            )
        if nova < inicio:
            return render(
                request,
                'estoque/partials/cautela_adiar_modal.html',
                _ctx(
                    {
                        'data_fim_inicial_iso': nova.isoformat(),
                        'data_inicio_iso': inicio.isoformat(),
                        'sugestao_7_iso': sug7.isoformat(),
                        'sugestao_30_iso': sug30.isoformat(),
                        'form_erro': (
                            'A previsão não pode ser anterior à data de início da cautela.'
                        ),
                    }
                ),
            )

        cautela.data_fim = nova
        cautela.save(update_fields=['data_fim'])
        registrar_auditoria(
            request,
            acao='update',
            resumo=(
                f'Previsão da cautela #{cautela.pk} atualizada para {nova:%d/%m/%Y}.'
            ),
            modulo='estoque',
            detalhes={'cautela_id': cautela.pk, 'operacao': 'adiar_prazo'},
        )
        messages.success(request, 'Previsão de entrega atualizada.')
        return _hx_redirect(
            request,
            'estoque:cautela_detalhe',
            kwargs={'pk': cautela.pk},
        )

    return render(
        request,
        'estoque/partials/cautela_adiar_modal.html',
        _ctx(
            {
                'data_fim_inicial_iso': data_fim_inicial_iso,
                'data_inicio_iso': inicio.isoformat(),
                'sugestao_7_iso': sug7.isoformat(),
                'sugestao_30_iso': sug30.isoformat(),
            }
        ),
    )


def _staff_cautela_negado(request, pk: int):
    messages.error(
        request,
        'Apenas utilizadores com acesso administrativo podem editar ou excluir cautelas por aqui.',
    )
    return redirect_empresa(request, 'estoque:cautela_detalhe', kwargs={'pk': pk})


@login_required
def editar_cautela_staff(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    if not request.user.is_staff:
        return _staff_cautela_negado(request, pk)

    cautela = get_object_or_404(
        Cautela.objects.select_related('funcionario', 'local', 'obra'),
        pk=pk,
        empresa=empresa,
    )

    if request.method == 'POST':
        form = CautelaStaffEditForm(
            request.POST,
            instance=cautela,
            empresa=empresa,
        )
        if form.is_valid():
            with transaction.atomic():
                locked = Cautela.objects.select_for_update().get(
                    pk=cautela.pk, empresa=empresa
                )
                obj = form.save(commit=False)
                pks_to_free: list[int] = []
                if obj.situacao == Cautela.Situacao.INATIVA:
                    pks_to_free = list(
                        locked.ferramentas.values_list('pk', flat=True)
                    )
                obj.save()
                if pks_to_free:
                    Ferramenta.objects.filter(
                        pk__in=pks_to_free, empresa=empresa
                    ).update(situacao_cautela=Ferramenta.SituacaoCautela.LIVRE)
                    locked.ferramentas.clear()

            registrar_auditoria(
                request,
                acao='update',
                resumo=f'Cautela #{cautela.pk} atualizada (admin).',
                modulo='estoque',
                detalhes={'cautela_id': cautela.pk},
            )
            messages.success(request, 'Cautela atualizada.')
            return redirect_empresa(
                request, 'estoque:cautela_detalhe', kwargs={'pk': cautela.pk}
            )
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = CautelaStaffEditForm(instance=cautela, empresa=empresa)

    return render(
        request,
        'estoque/ferramentas/cautela_editar_staff.html',
        {
            'page_title': f'Editar cautela #{cautela.pk}',
            'cautela': cautela,
            'form': form,
        },
    )


@login_required
def excluir_cautela_staff(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    if not request.user.is_staff:
        return _staff_cautela_negado(request, pk)

    cautela = get_object_or_404(
        Cautela.objects.select_related('funcionario'),
        pk=pk,
        empresa=empresa,
    )

    if request.method == 'POST':
        cid = cautela.pk
        with transaction.atomic():
            locked = Cautela.objects.select_for_update().get(
                pk=cautela.pk, empresa=empresa
            )
            pks = list(locked.ferramentas.values_list('pk', flat=True))
            if pks:
                Ferramenta.objects.filter(pk__in=pks, empresa=empresa).update(
                    situacao_cautela=Ferramenta.SituacaoCautela.LIVRE
                )
            locked.delete()

        registrar_auditoria(
            request,
            acao='delete',
            resumo=f'Cautela #{cid} excluída (admin).',
            modulo='estoque',
            detalhes={'cautela_id': cid},
        )
        messages.success(request, 'Cautela excluída.')
        return redirect_empresa(request, 'estoque:cautela_ferramentas')

    return render(
        request,
        'estoque/ferramentas/cautela_excluir_staff.html',
        {
            'page_title': f'Excluir cautela #{cautela.pk}',
            'cautela': cautela,
        },
    )


@login_required
def nova_cautela(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    if request.method == 'GET' and request.GET.get('fresh') == '1':
        _excluir_rascunho_nova_cautela(empresa, request.user)

    if request.method == 'POST':
        form = CautelaForm(request.POST, empresa=empresa)
        raw_ids = request.POST.getlist('ferramentas_ids')
        ids: list[int] = []
        for r in raw_ids:
            try:
                rid = int(str(r).strip())
            except Exception:
                continue
            if rid not in ids:
                ids.append(rid)

        if not ids:
            messages.error(request, 'Selecione ao menos 1 ferramenta.')

        if form.is_valid() and ids:
            try:
                reserved_ids = set(
                    Ferramenta.objects.filter(
                        empresa=empresa,
                        ativo=True,
                        pk__in=ids,
                        situacao_cautela=Ferramenta.SituacaoCautela.OCUPADA,
                    ).values_list('pk', flat=True)
                )

                if reserved_ids:
                    messages.error(
                        request,
                        'Uma ou mais ferramentas já estão em cautela ativa. '
                        'Elas não podem ser selecionadas para uma nova cautela.',
                    )
                    # cai fora do try: volta ao render da página
                    raise ValueError('Ferramenta indisponível')

                ferrs = (
                    Ferramenta.objects.filter(
                        empresa=empresa, ativo=True, pk__in=ids
                    ).exclude(
                        situacao_cautela=Ferramenta.SituacaoCautela.OCUPADA
                    )
                    .select_related('categoria')
                    .distinct()
                )
                if ferrs.count() != len(set(ids)):
                    messages.error(
                        request,
                        'Uma ou mais ferramentas selecionadas são inválidas.',
                    )
                else:
                    with transaction.atomic():
                        obj = form.save(commit=False)
                        obj.empresa = empresa
                        obj.almoxarife = request.user
                        obj.situacao = Cautela.Situacao.ATIVA
                        obj.entrega = Cautela.Entrega.NAO
                        obj.save()
                        obj.ferramentas.set(ferrs)
                        Ferramenta.objects.filter(
                            pk__in=ferrs.values_list('pk', flat=True)
                        ).update(
                            situacao_cautela=Ferramenta.SituacaoCautela.OCUPADA
                        )

                        registrar_auditoria(
                            request,
                            acao='create',
                            resumo=f'Cautela #{obj.pk} cadastrada.',
                            modulo='estoque',
                            detalhes={'cautela_id': obj.pk},
                        )

                    messages.success(request, 'Cautela cadastrada.')
                    _excluir_rascunho_nova_cautela(empresa, request.user)
                    return redirect(
                        reverse_empresa(request, 'estoque:cautela_ferramentas')
                    )
            except Exception:
                messages.error(
                    request, 'Não foi possível cadastrar a cautela. Tente de novo.'
                )
        else:
            messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = CautelaForm(empresa=empresa)

    almoxarife_label = request.user.nome_completo or request.user.username

    if request.method == 'POST':
        rascunho_inicial = _rascunho_nova_cautela_de_post(request, empresa)
    else:
        row = _obter_rascunho_nova_cautela(empresa, request.user)
        rascunho_inicial = row.dados if row else None

    return render(
        request,
        'estoque/ferramentas/nova_cautela.html',
        {
            'page_title': 'Nova cautela de ferramentas',
            'form': form,
            'almoxarife_label': almoxarife_label,
            'hoje_iso': timezone.localdate().isoformat(),
            'rascunho_inicial': rascunho_inicial,
            'rascunho_save_url': reverse_empresa(
                request, 'estoque:api_rascunho_nova_cautela'
            ),
        },
    )


@login_required
@require_http_methods(['GET', 'POST', 'DELETE'])
def api_rascunho_nova_cautela(request):
    empresa = _empresa(request)
    if not empresa:
        return JsonResponse({'ok': False, 'error': 'empresa'}, status=403)

    if request.method == 'GET':
        row = _obter_rascunho_nova_cautela(empresa, request.user)
        dados = row.dados if row else {'form': {}, 'items': []}
        return JsonResponse(dados)

    if request.method == 'DELETE':
        _excluir_rascunho_nova_cautela(empresa, request.user)
        return JsonResponse({'ok': True})

    ct = (request.content_type or '').split(';')[0].strip()
    if ct != 'application/json':
        return JsonResponse({'ok': False, 'error': 'content_type'}, status=415)

    try:
        raw = request.body[:_RASCUNHO_BODY_MAX].decode('utf-8')
        payload = json.loads(raw)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'json'}, status=400)

    dados = _sanitizar_rascunho_nova_cautela(payload)
    RascunhoNovaCautela.objects.update_or_create(
        empresa=empresa,
        usuario=request.user,
        defaults={'dados': dados},
    )
    return JsonResponse({'ok': True})


@login_required
def modal_nova_cautela(request):
    # Mantido apenas por compatibilidade de URL anterior.
    return redirect_empresa(request, 'estoque:cautela_nova')


@login_required
def modal_buscar_itens_cautela(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:cautela_nova')

    return render(
        request,
        'estoque/partials/cautela_buscar_itens_modal.html',
        {},
    )


@login_required
def partial_buscar_itens_cautela(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:cautela_nova')

    q = (request.GET.get('q') or '').strip()

    if not q:
        return render(
            request,
            'estoque/ferramentas/partials/_buscar_ferramentas_cautela_lista.html',
            {'page_obj': [], 'hint': 'Digite para buscar.'},
        )

    ferramentes = (
        Ferramenta.objects.filter(empresa=empresa, ativo=True)
        .select_related('categoria')
        .prefetch_related('imagens')
        .order_by('descricao')
    )

    # UI usa `Ferramenta.situacao_cautela` (persistido) para mostrar LIVRE/OCUPADA.

    q_filter = (
        Q(descricao__icontains=q)
        | Q(marca__icontains=q)
        | Q(categoria__nome__icontains=q)
        | Q(codigo_numeracao__icontains=q)
        | Q(cor__icontains=q)
    )
    if q.isdigit():
        q_filter |= Q(pk=int(q))

    ferramentes = ferramentes.filter(q_filter)

    paginator = Paginator(ferramentes, 20)
    page_param = request.GET.get('page') or 1
    try:
        page_obj = paginator.page(page_param)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(
        request,
        'estoque/ferramentas/partials/_buscar_ferramentas_cautela_lista.html',
        {'page_obj': page_obj, 'hint': ''},
    )


@login_required
def modal_entrega_cautela(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    cautela = get_object_or_404(
        Cautela.objects.select_related('funcionario', 'almoxarife', 'local', 'obra').prefetch_related(
            Prefetch(
                'ferramentas',
                queryset=Ferramenta.objects.select_related('categoria').order_by(
                    'descricao'
                ),
            ),
        ),
        pk=pk,
        empresa=empresa,
    )

    if not _is_htmx(request):
        return redirect_empresa(
            request, 'estoque:cautela_detalhe', kwargs={'pk': pk}
        )

    post_url = reverse_empresa(
        request, 'estoque:modal_entrega_cautela', kwargs={'pk': cautela.pk}
    )

    modo = request.GET.get('devolucao', 'parcial') if request.method == 'GET' else None
    if request.method == 'POST':
        modo = request.POST.get('devolucao_modo', 'parcial')
    if modo not in ('parcial', 'total'):
        modo = 'parcial'

    titulo_modal = (
        f'Devolução total — Cautela #{cautela.pk}'
        if modo == 'total'
        else f'Devolução parcial — Cautela #{cautela.pk}'
    )

    catalogos_ok = _devolucao_catalogos_prontos(empresa)
    bloqueada = cautela.situacao == Cautela.Situacao.INATIVA
    sem_ferramentas = cautela.ferramentas.count() == 0

    def _ctx(form=None, extra=None):
        ctx = {
            'cautela': cautela,
            'form': form,
            'post_url': post_url,
            'titulo_modal': titulo_modal,
            'modo_devolucao': modo,
            'entrega_bloqueada': bloqueada,
            'catalogos_ok': catalogos_ok,
            'sem_ferramentas': sem_ferramentas,
        }
        if extra:
            ctx.update(extra)
        return ctx

    if bloqueada or sem_ferramentas or not catalogos_ok:
        return render(
            request,
            'estoque/partials/entrega_cautela_form_modal.html',
            _ctx(),
        )

    if request.method == 'POST':
        form = EntregaCautelaDevolucaoForm(request.POST, empresa=empresa)
        if modo == 'parcial':
            ids_pre = _parse_ferramentas_devolucao_ids(request)
        else:
            ids_pre = list(cautela.ferramentas.values_list('pk', flat=True))

        ids_set_pre = set(ids_pre)
        no_snapshot = set(cautela.ferramentas.values_list('pk', flat=True))

        pode_salvar = form.is_valid()
        if modo == 'parcial' and not ids_set_pre:
            form.add_error(
                None,
                'Selecione ao menos uma ferramenta para devolução parcial.',
            )
            pode_salvar = False
        elif not ids_set_pre or not ids_set_pre <= no_snapshot:
            form.add_error(
                None,
                'Ferramentas inválidas ou já retiradas desta cautela.',
            )
            pode_salvar = False

        if pode_salvar:
            data_entrega = form.cleaned_data['data_entrega']
            observacoes = form.cleaned_data.get('observacoes') or ''
            motivo = form.cleaned_data['motivo']
            situacao_f = form.cleaned_data['situacao_ferramentas']

            with transaction.atomic():
                locked = Cautela.objects.select_for_update().get(
                    pk=cautela.pk, empresa=empresa
                )

                if locked.situacao == Cautela.Situacao.INATIVA:
                    messages.error(request, 'Esta cautela já está inativa.')
                    return render(
                        request,
                        'estoque/partials/entrega_cautela_form_modal.html',
                        _ctx(form),
                        status=409,
                    )

                no_cautela = set(
                    locked.ferramentas.values_list('pk', flat=True)
                )
                if modo == 'total':
                    ids_devolucao = list(no_cautela)
                else:
                    ids_devolucao = list(ids_set_pre)
                ids_set = set(ids_devolucao)

                if not ids_set or not ids_set <= no_cautela:
                    messages.error(
                        request,
                        'Os dados da cautela mudaram. Feche o modal e tente de novo.',
                    )
                    return render(
                        request,
                        'estoque/partials/entrega_cautela_form_modal.html',
                        _ctx(form),
                    )
                else:
                    ferramentas_a_livrar = list(
                        Ferramenta.objects.filter(
                            empresa=empresa,
                            pk__in=ids_devolucao,
                        )
                    )
                    if len(ferramentas_a_livrar) != len(ids_set):
                        messages.error(
                            request,
                            'Não foi possível localizar as ferramentas para devolução.',
                        )
                        return render(
                            request,
                            'estoque/partials/entrega_cautela_form_modal.html',
                            _ctx(form),
                        )

                    tipo_registro = (
                        Entrega_Cautela.Tipo.COMPLETA
                        if ids_set == no_cautela
                        else Entrega_Cautela.Tipo.PARCIAL
                    )

                    entrega = Entrega_Cautela.objects.create(
                        cautela=locked,
                        tipo=tipo_registro,
                        data_entrega=data_entrega,
                        observacoes=observacoes,
                        motivo=motivo,
                        situacao_ferramentas=situacao_f,
                    )
                    entrega.ferramentas_devolvidas.set(ferramentas_a_livrar)

                    pks_livrar = [f.pk for f in ferramentas_a_livrar]
                    Ferramenta.objects.filter(pk__in=pks_livrar).update(
                        situacao_cautela=Ferramenta.SituacaoCautela.LIVRE
                    )
                    locked.ferramentas.remove(*ferramentas_a_livrar)

                    restantes = locked.ferramentas.count()
                    if restantes == 0:
                        locked.entrega = Cautela.Entrega.TOTAL
                        locked.situacao = Cautela.Situacao.INATIVA
                        locked.data_fim = data_entrega
                        operacao = 'entrega_completa'
                    else:
                        locked.entrega = Cautela.Entrega.PARCIAL
                        locked.situacao = Cautela.Situacao.ATIVA
                        locked.data_fim = None
                        operacao = 'entrega_parcial'

                    locked.save(
                        update_fields=['entrega', 'situacao', 'data_fim']
                    )

                    registrar_auditoria(
                        request,
                        acao='create',
                        resumo=(
                            f'Devolução da cautela #{locked.pk} ({locked.get_entrega_display()}).'
                        ),
                        modulo='estoque',
                        detalhes={
                            'cautela_id': locked.pk,
                            'operacao': operacao,
                            'entrega_id': entrega.pk,
                        },
                    )

                    messages.success(request, 'Devolução registrada.')
                    return _hx_redirect(
                        request,
                        'estoque:cautela_detalhe',
                        kwargs={'pk': locked.pk},
                    )

        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = EntregaCautelaDevolucaoForm(
            empresa=empresa,
            initial={'data_entrega': timezone.localdate()},
        )

    return render(
        request,
        'estoque/partials/entrega_cautela_form_modal.html',
        _ctx(form),
    )

