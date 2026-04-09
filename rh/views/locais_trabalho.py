from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

import json
import math

from local.models import Local, LocalTrabalhoAtivo

from ..models import Funcionario
from .base import _empresa_ativa_or_redirect


def _is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def _context_locais_trabalho(empresa_ativa):
    locais = list(
        Local.objects.filter(empresa=empresa_ativa).order_by('nome', 'id')
    )
    locais_ativos = list(
        LocalTrabalhoAtivo.objects.filter(empresa=empresa_ativa)
        .select_related('local')
        .order_by('local__nome', 'id')
    )

    funcionarios = list(
        Funcionario.objects.filter(empresa=empresa_ativa)
        .exclude(situacao_atual__in=['demitido', 'inativo'])
        .select_related('cargo', 'local_trabalho')
        .order_by('nome', 'id')
    )

    ativos_ids = {a.local_id for a in locais_ativos}
    por_local = {a.local_id: [] for a in locais_ativos}
    sem_local = []
    for f in funcionarios:
        if f.local_trabalho_id and f.local_trabalho_id in ativos_ids:
            por_local[f.local_trabalho_id].append(f)
        else:
            sem_local.append(f)

    locais_cards = [{'local': a.local, 'pessoas': por_local.get(a.local_id, [])} for a in locais_ativos]

    return {
        'locais': locais,
        'locais_ativos': locais_ativos,
        'funcionarios': funcionarios,
        'locais_cards': locais_cards,
        'sem_local': sem_local,
    }


@login_required
def locais_trabalho(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para visualizar os locais de trabalho.',
    )
    if redirect_response:
        return redirect_response

    context = {'page_title': 'Locais de Trabalho', **_context_locais_trabalho(empresa_ativa)}
    return render(request, 'rh/locais_trabalho.html', context)


@login_required
def locais_trabalho_mapa(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.',
    )
    if redirect_response:
        return redirect_response

    locais_ativos = list(
        LocalTrabalhoAtivo.objects.filter(empresa=empresa_ativa)
        .select_related('local')
        .order_by('local__nome', 'id')
    )
    ativos_ids = [a.local_id for a in locais_ativos]

    funcionarios = list(
        Funcionario.objects.filter(empresa=empresa_ativa, local_trabalho_id__in=ativos_ids)
        .exclude(situacao_atual__in=['demitido', 'inativo'])
        .select_related('local_trabalho')
        .order_by('local_trabalho__nome', 'nome', 'id')
    )

    por_local = {}
    for f in funcionarios:
        por_local.setdefault(f.local_trabalho_id, []).append(f)

    markers = []
    locais_sem_coords = 0
    for a in locais_ativos:
        loc = a.local
        if loc.latitude is None or loc.longitude is None:
            locais_sem_coords += 1
            continue
        pessoas = por_local.get(loc.pk, [])
        employees = []
        for f in pessoas:
            foto_url = None
            if getattr(f, 'foto', None):
                try:
                    foto_url = f.foto.url
                except Exception:
                    foto_url = None
            employees.append({'id': f.pk, 'nome': f.nome, 'foto_url': foto_url})

        markers.append(
            {
                'lat': float(loc.latitude),
                'lng': float(loc.longitude),
                'local_id': loc.pk,
                'local_nome': loc.nome,
                'qtd': len(employees),
                'employees': employees,
            }
        )

    return render(
        request,
        'rh/locais_trabalho_mapa.html',
        {
            'page_title': 'Mapa — Locais de Trabalho',
            'markers': markers,
            'funcionarios_alocados_count': len(funcionarios),
            'locais_ativos_count': len(locais_ativos),
            'locais_sem_coords': locais_sem_coords,
        },
    )


@login_required
def locais_trabalho_board(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.',
    )
    if redirect_response:
        return redirect_response
    return render(
        request,
        'rh/locais_trabalho/_board.html',
        _context_locais_trabalho(empresa_ativa),
    )


@login_required
@require_POST
def definir_local_trabalho_funcionario(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.',
    )
    if redirect_response:
        return redirect_response

    funcionario_id = request.POST.get('funcionario_id')
    local_id = (request.POST.get('local_id') or '').strip()

    try:
        funcionario_id = int(funcionario_id)
    except (TypeError, ValueError):
        return HttpResponse('Funcionário inválido.', status=400, content_type='text/plain; charset=utf-8')

    func = Funcionario.objects.filter(pk=funcionario_id, empresa=empresa_ativa).first()
    if not func:
        return HttpResponse('Funcionário não encontrado.', status=404, content_type='text/plain; charset=utf-8')

    novo_local = None
    if local_id:
        try:
            local_id_int = int(local_id)
        except (TypeError, ValueError):
            return HttpResponse('Local inválido.', status=400, content_type='text/plain; charset=utf-8')

        novo_local = Local.objects.filter(pk=local_id_int, empresa=empresa_ativa).first()
        if not novo_local:
            return HttpResponse('Local não encontrado.', status=404, content_type='text/plain; charset=utf-8')

    func.local_trabalho = novo_local
    func.save(update_fields=['local_trabalho'])

    if novo_local:
        messages.success(request, f'{func.nome} atribuído(a) ao local: {novo_local.nome}.')
    else:
        messages.success(request, f'Local removido de {func.nome}.')

    response = HttpResponse(status=204)
    if _is_htmx(request):
        response['HX-Refresh'] = 'true'
    return response


@login_required
@require_POST
def definir_local_trabalho_funcionario_json(request):
    """
    Endpoint para drag&drop (fetch): define o local_trabalho pelo body JSON.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.',
    )
    if redirect_response:
        return redirect_response

    try:
        payload = request.body.decode() or '{}'
    except Exception:
        payload = '{}'

    try:
        data = json.loads(payload)
    except Exception:
        return HttpResponse('JSON inválido.', status=400, content_type='text/plain; charset=utf-8')

    funcionario_id = data.get('funcionario_id')
    local_id = data.get('local_id')

    try:
        funcionario_id = int(funcionario_id)
    except (TypeError, ValueError):
        return HttpResponse('Funcionário inválido.', status=400, content_type='text/plain; charset=utf-8')

    if local_id in (None, '', 0, '0'):
        local_id = None
    else:
        try:
            local_id = int(local_id)
        except (TypeError, ValueError):
            return HttpResponse('Local inválido.', status=400, content_type='text/plain; charset=utf-8')

    func = Funcionario.objects.filter(pk=funcionario_id, empresa=empresa_ativa).first()
    if not func:
        return HttpResponse('Funcionário não encontrado.', status=404, content_type='text/plain; charset=utf-8')

    novo_local = None
    if local_id:
        # só permite atribuir para locais ativos
        ativo = LocalTrabalhoAtivo.objects.filter(empresa=empresa_ativa, local_id=local_id).exists()
        if not ativo:
            return HttpResponse('Local não está ativo.', status=400, content_type='text/plain; charset=utf-8')
        novo_local = Local.objects.filter(pk=local_id, empresa=empresa_ativa).first()
        if not novo_local:
            return HttpResponse('Local não encontrado.', status=404, content_type='text/plain; charset=utf-8')

    func.local_trabalho = novo_local
    func.save(update_fields=['local_trabalho'])
    return HttpResponse(status=204)


@login_required
@require_POST
def ativar_local_trabalho(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.',
    )
    if redirect_response:
        return redirect_response

    local_id = (request.POST.get('local_id') or '').strip()
    try:
        local_id = int(local_id)
    except (TypeError, ValueError):
        return HttpResponse('Local inválido.', status=400, content_type='text/plain; charset=utf-8')

    loc = Local.objects.filter(pk=local_id, empresa=empresa_ativa).first()
    if not loc:
        return HttpResponse('Local não encontrado.', status=404, content_type='text/plain; charset=utf-8')

    # Se não houver coordenadas, tenta extrair de links do Maps ao ativar.
    if (loc.latitude is None or loc.longitude is None):
        src = (getattr(loc, 'link_maps_embed', '') or '').strip()
        lat, lng = Local.parse_lat_lng_from_maps(src)
        if lat is not None and lng is not None:
            loc.latitude = lat
            loc.longitude = lng
            loc.save(update_fields=['latitude', 'longitude'])

    obj, created = LocalTrabalhoAtivo.objects.get_or_create(empresa=empresa_ativa, local=loc)
    if created:
        messages.success(request, f'Local ativado: {loc.nome}.')
    else:
        messages.info(request, f'Este local já está ativo: {loc.nome}.')

    if _is_htmx(request):
        return render(
            request,
            'rh/locais_trabalho/_board.html',
            _context_locais_trabalho(empresa_ativa),
        )
    return HttpResponse(status=204)


@login_required
@require_POST
def desativar_local_trabalho(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.',
    )
    if redirect_response:
        return redirect_response

    local_id = (request.POST.get('local_id') or '').strip()
    try:
        local_id = int(local_id)
    except (TypeError, ValueError):
        return HttpResponse('Local inválido.', status=400, content_type='text/plain; charset=utf-8')

    ativo = (
        LocalTrabalhoAtivo.objects.filter(empresa=empresa_ativa, local_id=local_id)
        .select_related('local')
        .first()
    )
    if not ativo:
        return HttpResponse('Local ativo não encontrado.', status=404, content_type='text/plain; charset=utf-8')

    with transaction.atomic():
        Funcionario.objects.filter(empresa=empresa_ativa, local_trabalho_id=local_id).update(local_trabalho=None)
        ativo.delete()

    messages.success(request, f'Local desativado: {ativo.local.nome}. Funcionários devolvidos para “Sem local”.')
    if _is_htmx(request):
        return render(
            request,
            'rh/locais_trabalho/_board.html',
            _context_locais_trabalho(empresa_ativa),
        )
    return HttpResponse(status=204)


@login_required
def buscar_locais_trabalho(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.',
    )
    if redirect_response:
        return redirect_response

    q = (request.GET.get('q') or '').strip()
    qs = Local.objects.filter(empresa=empresa_ativa).order_by('nome', 'id')
    if q:
        qs = qs.filter(nome__icontains=q)

    ativos_ids = set(
        LocalTrabalhoAtivo.objects.filter(empresa=empresa_ativa).values_list('local_id', flat=True)
    )

    locais = list(qs[:20])
    context = {
        'q': q,
        'locais_result': locais,
        'ativos_ids': ativos_ids,
    }
    return render(request, 'rh/locais_trabalho/_locais_sugestoes.html', context)


@login_required
def modal_ativar_local_trabalho(request, local_pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.',
    )
    if redirect_response:
        return redirect_response

    loc = Local.objects.filter(pk=local_pk, empresa=empresa_ativa).first()
    if not loc:
        return HttpResponse('Local não encontrado.', status=404, content_type='text/plain; charset=utf-8')

    ja_ativo = LocalTrabalhoAtivo.objects.filter(empresa=empresa_ativa, local=loc).exists()
    return render(
        request,
        'rh/locais_trabalho/_modal_ativar_local.html',
        {'local': loc, 'ja_ativo': ja_ativo},
    )


@login_required
def modal_detalhes_local_trabalho(request, local_pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.',
    )
    if redirect_response:
        return redirect_response

    ativo = (
        LocalTrabalhoAtivo.objects.filter(empresa=empresa_ativa, local_id=local_pk)
        .select_related('local')
        .first()
    )
    if not ativo:
        return HttpResponse('Local não está ativo.', status=404, content_type='text/plain; charset=utf-8')

    loc = ativo.local
    qtd = Funcionario.objects.filter(empresa=empresa_ativa, local_trabalho=loc).count()
    return render(
        request,
        'rh/locais_trabalho/_modal_detalhes_local.html',
        {'local': loc, 'qtd_funcionarios': qtd},
    )

