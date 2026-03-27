from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from controles_rh.models import Competencia


@login_required
def home_controles_rh(request):
    empresa_ativa = getattr(request, 'empresa_ativa', None)

    competencias = Competencia.objects.none()
    anos_disponiveis = []

    filtro_ano = request.GET.get('ano', '').strip()
    filtro_status = request.GET.get('status', 'aberta').strip() or 'aberta'

    if empresa_ativa:
        base_qs = Competencia.objects.filter(empresa=empresa_ativa)

        anos_disponiveis = list(
            base_qs.order_by('-ano')
            .values_list('ano', flat=True)
            .distinct()
        )

        competencias = base_qs

        if filtro_ano:
            try:
                competencias = competencias.filter(ano=int(filtro_ano))
            except ValueError:
                pass

        if filtro_status == 'aberta':
            competencias = competencias.filter(fechada=False)
        elif filtro_status == 'fechada':
            competencias = competencias.filter(fechada=True)
        elif filtro_status == 'todas':
            pass
        else:
            filtro_status = 'aberta'
            competencias = competencias.filter(fechada=False)

        competencias = competencias.order_by('-ano', '-mes', '-id')

    context = {
        'page_title': 'Gestão RH',
        'empresa_ativa': empresa_ativa,
        'competencias': competencias,
        'anos_disponiveis': anos_disponiveis,
        'filtro_ano': filtro_ano,
        'filtro_status': filtro_status,
    }
    return render(request, 'controles_rh/home.html', context)