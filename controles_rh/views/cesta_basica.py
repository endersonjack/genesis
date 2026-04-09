import json
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch
from django.utils import timezone

from core.urlutils import redirect_empresa, reverse_empresa
from django.views.decorators.http import require_POST

from auditoria.registry import audit_controles_rh

from controles_rh.forms import CestaBasicaItemForm, CestaBasicaListaForm
from controles_rh.models import CestaBasicaItem, CestaBasicaLista
from controles_rh.views.competencias import _get_competencia_empresa
from rh.models import Funcionario


def _is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def _get_empresa_ativa(request):
    return getattr(request, 'empresa_ativa', None)


def _get_lista_cesta_empresa(request, pk):
    empresa_ativa = _get_empresa_ativa(request)
    qs = CestaBasicaLista.objects.select_related('competencia', 'competencia__empresa')
    if empresa_ativa:
        qs = qs.filter(competencia__empresa=empresa_ativa)
    else:
        qs = qs.none()
    return get_object_or_404(qs, pk=pk)


def _url_recibo_individual_item(request, item_pk):
    """URL do PDF de recibo individual; fallback se o nome da rota ainda não estiver carregado."""
    try:
        return reverse_empresa(
            request,
            'controles_rh:exportar_recibo_cesta_individual_item',
            kwargs={'pk': item_pk},
        )
    except (NoReverseMatch, ValueError):
        prefix = (getattr(request, 'script_name', None) or '').rstrip('/')
        eid = getattr(getattr(request, 'empresa_ativa', None), 'pk', '') or ''
        return f'{prefix}/empresa/{eid}/rh/gestao/cesta-basica/itens/{item_pk}/recibo/pdf/'


def _get_item_cesta_empresa(request, pk):
    empresa_ativa = _get_empresa_ativa(request)
    qs = CestaBasicaItem.objects.select_related(
        'lista',
        'lista__competencia',
        'lista__competencia__empresa',
        'funcionario',
    )
    if empresa_ativa:
        qs = qs.filter(lista__competencia__empresa=empresa_ativa)
    else:
        qs = qs.none()
    return get_object_or_404(qs, pk=pk)


@login_required
def criar_cesta_basica(request, competencia_pk):
    """Cria uma nova lista de Cesta Básica na competência e abre o detalhe."""
    competencia = _get_competencia_empresa(request, competencia_pk)
    n = CestaBasicaLista.objects.filter(competencia=competencia).count() + 1
    titulo = 'Cesta Básica' if n == 1 else f'Cesta Básica {n}'
    lista = CestaBasicaLista.objects.create(competencia=competencia, titulo=titulo)
    audit_controles_rh(
        request,
        'create',
        f'Lista de cesta básica criada: {titulo} ({competencia.referencia}).',
        {'cesta_lista_id': lista.pk, 'competencia_id': competencia.pk},
    )
    return redirect_empresa(request, 'controles_rh:detalhe_cesta_basica', pk=lista.pk)


@login_required
def detalhe_cesta_basica(request, pk):
    lista = _get_lista_cesta_empresa(request, pk)
    itens_qs = lista.itens.select_related('funcionario').order_by('ordem', 'nome', 'id')
    ativos = itens_qs.filter(ativo=True)
    itens = list(itens_qs)
    for item in itens:
        item.recibo_item_url = _url_recibo_individual_item(request, item.pk)
    context = {
        'page_title': f'Cesta Básica — {lista.competencia.referencia}',
        'lista': lista,
        'competencia': lista.competencia,
        'itens': itens,
        'total_itens': len(itens),
        'total_ativos': ativos.count(),
        'total_recebidos': ativos.filter(recebido=True).count(),
    }
    return render(request, 'controles_rh/cesta_basica/detalhe.html', context)


@login_required
@require_POST
def definir_recebido_item_cesta_basica(request, pk):
    item = _get_item_cesta_empresa(request, pk)
    raw = request.POST.get('recebido')
    if raw in ('true', 'True', '1', 'on', 'yes'):
        item.recebido = True
        if not item.data_recebimento:
            item.data_recebimento = date.today()
    elif raw in ('false', 'False', '0', 'off', 'no', ''):
        item.recebido = False
        item.data_recebimento = None
    else:
        item.recebido = not item.recebido
        if item.recebido and not item.data_recebimento:
            item.data_recebimento = date.today()
        elif not item.recebido:
            item.data_recebimento = None
    item.save(update_fields=['recebido', 'data_recebimento', 'data_atualizacao'])
    audit_controles_rh(
        request,
        'update',
        f'Recebimento de cesta atualizado — {item.nome_exibicao}.',
        {'cesta_item_id': item.pk, 'cesta_lista_id': item.lista_id},
    )
    response = HttpResponse(status=204)
    if _is_htmx(request):
        response['HX-Refresh'] = 'true'
    return response


@login_required
@require_POST
def limpar_recebido_cesta_basica(request, lista_pk):
    """Zera Recebeu e data de recebimento em todas as linhas da lista."""
    lista = _get_lista_cesta_empresa(request, lista_pk)
    lista.itens.update(
        recebido=False,
        data_recebimento=None,
        data_atualizacao=timezone.now(),
    )
    audit_controles_rh(
        request,
        'update',
        f'Recebimentos de cesta limpos — {lista.titulo}.',
        {'cesta_lista_id': lista.pk},
    )
    messages.success(request, 'Todas as marcações de recebimento foram limpas.')
    response = HttpResponse(status=204)
    if _is_htmx(request):
        response['HX-Refresh'] = 'true'
    return response


@login_required
@require_POST
def receber_todos_cesta_basica(request, lista_pk):
    """Marca todas as linhas como recebidas com data de recebimento = hoje."""
    lista = _get_lista_cesta_empresa(request, lista_pk)
    hoje = date.today()
    n = lista.itens.update(
        recebido=True,
        data_recebimento=hoje,
        data_atualizacao=timezone.now(),
    )
    if n:
        audit_controles_rh(
            request,
            'update',
            f'Todas as linhas marcadas como recebidas — {lista.titulo} ({n} linhas).',
            {'cesta_lista_id': lista.pk},
        )
        messages.success(
            request,
            f'Todas as linhas foram marcadas como recebidas em {hoje.strftime("%d/%m/%Y")}.',
        )
    else:
        messages.info(request, 'Não há linhas nesta lista.')
    response = HttpResponse(status=204)
    if _is_htmx(request):
        response['HX-Refresh'] = 'true'
    return response


@login_required
@require_POST
def adicionar_todos_funcionarios_cesta_basica(request, lista_pk):
    """
    Adiciona todos os funcionários admitidos da empresa à lista.
    Não duplica quem já estiver presente via FK `funcionario`.
    """
    lista = _get_lista_cesta_empresa(request, lista_pk)
    empresa = lista.competencia.empresa

    # Funcionários elegíveis (mesmo filtro do form)
    funcs = (
        Funcionario.objects.filter(empresa=empresa, situacao_atual='admitido')
        .select_related('cargo', 'lotacao')
        .order_by('nome', 'id')
    )

    existentes_ids = set(
        lista.itens.exclude(funcionario_id__isnull=True).values_list('funcionario_id', flat=True)
    )

    ultima_ordem = lista.itens.order_by('-ordem').values_list('ordem', flat=True).first() or 0
    novos = []
    ordem = ultima_ordem
    for f in funcs:
        if f.pk in existentes_ids:
            continue
        ordem += 1
        cargo = getattr(f, 'cargo', None)
        lot = getattr(f, 'lotacao', None)
        novos.append(
            CestaBasicaItem(
                lista=lista,
                funcionario=f,
                nome=getattr(f, 'nome', '') or '',
                funcao=str(cargo) if cargo else '',
                lotacao=(lot.nome if getattr(lot, 'nome', None) else ''),
                ordem=ordem,
                ativo=True,
                recebido=False,
                data_recebimento=None,
            )
        )

    if not novos:
        messages.info(request, 'Todos os funcionários admitidos já estão na lista.')
        response = HttpResponse(status=204)
        if _is_htmx(request):
            response['HX-Refresh'] = 'true'
        return response

    with transaction.atomic():
        # bulk_create não chama save()/clean(): já preenchemos os campos derivados.
        CestaBasicaItem.objects.bulk_create(novos, batch_size=500)

    audit_controles_rh(
        request,
        'create',
        f'Funcionários adicionados em massa à cesta básica — {lista.titulo} ({len(novos)} linhas).',
        {'cesta_lista_id': lista.pk, 'qtd_itens': len(novos)},
    )
    messages.success(request, f'{len(novos)} funcionário(s) adicionados à lista.')
    response = HttpResponse(status=204)
    if _is_htmx(request):
        response['HX-Refresh'] = 'true'
    return response


@login_required
def editar_cesta_basica_lista(request, pk):
    lista = _get_lista_cesta_empresa(request, pk)
    form = CestaBasicaListaForm(request.POST or None, instance=lista)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            audit_controles_rh(
                request,
                'update',
                f'Dados do recibo de cesta atualizados — {lista.titulo}.',
                {'cesta_lista_id': lista.pk},
            )
            messages.success(request, 'Dados do recibo atualizados.')
            if _is_htmx(request):
                response = HttpResponse(status=204)
                response['HX-Refresh'] = 'true'
                return response
            return redirect_empresa(request, 'controles_rh:detalhe_cesta_basica', pk=lista.pk)
        messages.error(request, 'Revise os campos.')

    context = {
        'lista': lista,
        'competencia': lista.competencia,
        'form': form,
    }
    return render(request, 'controles_rh/cesta_basica/_form_lista_modal.html', context)


@login_required
def excluir_cesta_basica_lista(request, pk):
    lista = _get_lista_cesta_empresa(request, pk)
    competencia = lista.competencia

    if request.method == 'POST':
        titulo = lista.titulo
        lid = lista.pk
        cid = competencia.pk
        lista.delete()
        audit_controles_rh(
            request,
            'delete',
            f'Lista de cesta básica excluída: {titulo}.',
            {'cesta_lista_id': lid, 'competencia_id': cid},
        )
        messages.success(request, 'Controle de Cesta Básica removido desta competência.')
        if _is_htmx(request):
            response = HttpResponse(status=204)
            response['HX-Redirect'] = reverse_empresa(
                request,
                'controles_rh:detalhe_competencia',
                kwargs={'ano': competencia.ano, 'mes': competencia.mes},
            )
            return response
        return redirect_empresa(
            request,
            'controles_rh:detalhe_competencia',
            kwargs={'ano': competencia.ano, 'mes': competencia.mes},
        )

    context = {
        'lista': lista,
        'competencia': competencia,
    }
    return render(request, 'controles_rh/cesta_basica/_excluir_lista_modal.html', context)


@login_required
def adicionar_item_cesta_basica(request, lista_pk):
    lista = _get_lista_cesta_empresa(request, lista_pk)
    ultima_ordem = lista.itens.order_by('-ordem').values_list('ordem', flat=True).first() or 0

    form = CestaBasicaItemForm(
        request.POST or None,
        lista=lista,
        initial={'ordem': ultima_ordem + 1, 'ativo': True},
    )

    if request.method == 'POST':
        if form.is_valid():
            item = form.save()
            audit_controles_rh(
                request,
                'create',
                f'Linha de cesta adicionada: {item.nome_exibicao}.',
                {'cesta_item_id': item.pk, 'cesta_lista_id': lista.pk},
            )
            messages.success(request, f'Linha "{item.nome_exibicao}" adicionada.')
            if _is_htmx(request):
                response = HttpResponse(status=204)
                response['HX-Refresh'] = 'true'
                return response
            return redirect_empresa(request, 'controles_rh:detalhe_cesta_basica', pk=lista.pk)
        messages.error(request, 'Não foi possível adicionar a linha.')

    context = {
        'lista': lista,
        'competencia': lista.competencia,
        'item': None,
        'form': form,
        'modo': 'criar',
    }
    return render(request, 'controles_rh/cesta_basica/_form_item_modal.html', context)


@login_required
def editar_item_cesta_basica(request, pk):
    item = _get_item_cesta_empresa(request, pk)
    lista = item.lista

    form = CestaBasicaItemForm(
        request.POST or None,
        instance=item,
        lista=lista,
    )

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            audit_controles_rh(
                request,
                'update',
                f'Linha de cesta atualizada: {item.nome_exibicao}.',
                {'cesta_item_id': item.pk, 'cesta_lista_id': lista.pk},
            )
            messages.success(request, f'Linha "{item.nome_exibicao}" atualizada.')
            if _is_htmx(request):
                response = HttpResponse(status=204)
                response['HX-Refresh'] = 'true'
                return response
            return redirect_empresa(request, 'controles_rh:detalhe_cesta_basica', pk=lista.pk)
        messages.error(request, 'Não foi possível atualizar a linha.')

    context = {
        'lista': lista,
        'competencia': lista.competencia,
        'item': item,
        'form': form,
        'modo': 'editar',
    }
    return render(request, 'controles_rh/cesta_basica/_form_item_modal.html', context)


@login_required
def excluir_item_cesta_basica(request, pk):
    item = _get_item_cesta_empresa(request, pk)
    lista = item.lista

    if request.method == 'POST':
        nome = item.nome_exibicao
        lista_pk = lista.pk
        iid = item.pk
        item.delete()
        audit_controles_rh(
            request,
            'delete',
            f'Linha de cesta excluída: {nome}.',
            {'cesta_item_id': iid, 'cesta_lista_id': lista_pk},
        )
        messages.success(request, f'Linha "{nome}" excluída.')
        if _is_htmx(request):
            response = HttpResponse(status=204)
            response['HX-Refresh'] = 'true'
            return response
        return redirect_empresa(request, 'controles_rh:detalhe_cesta_basica', pk=lista_pk)

    context = {
        'item': item,
        'lista': lista,
        'competencia': lista.competencia,
    }
    return render(request, 'controles_rh/cesta_basica/_excluir_item_modal.html', context)


@login_required
@require_POST
def reordenar_itens_cesta_basica(request, lista_pk):
    lista = _get_lista_cesta_empresa(request, lista_pk)

    try:
        payload = json.loads(request.body.decode() or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'JSON inválido.'}, status=400)

    ids = payload.get('ids')
    if not isinstance(ids, list) or not ids:
        return JsonResponse({'ok': False, 'error': 'Informe a lista ids.'}, status=400)

    try:
        id_list = [int(x) for x in ids]
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'ids deve conter inteiros.'}, status=400)

    valid_ids = set(lista.itens.values_list('id', flat=True))
    if set(id_list) != valid_ids or len(id_list) != len(valid_ids):
        return JsonResponse({'ok': False, 'error': 'Lista de itens incompleta ou inválida.'}, status=400)

    with transaction.atomic():
        for ordem, item_id in enumerate(id_list, start=1):
            CestaBasicaItem.objects.filter(pk=item_id, lista=lista).update(ordem=ordem)

    audit_controles_rh(
        request,
        'update',
        f'Ordem das linhas de cesta atualizada — {lista.titulo}.',
        {'cesta_lista_id': lista.pk},
    )
    return JsonResponse({'ok': True})
