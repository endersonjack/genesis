from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.urlutils import is_safe_internal_path, redirect_empresa

from .models import Alerta
from .permissions import filtrar_alertas_permitidos


def _empresa(request):
    return getattr(request, 'empresa_ativa', None)


def _alertas_visiveis(request):
    empresa = _empresa(request)
    qs = Alerta.objects.filter(empresa=empresa).filter(
        Q(usuario__isnull=True) | Q(usuario=request.user)
    )
    return filtrar_alertas_permitidos(request, qs)


def _redirect_after_action(request):
    destino = request.POST.get('next') or request.META.get('HTTP_REFERER') or ''
    if is_safe_internal_path(destino):
        return redirect(destino)
    return redirect_empresa(request, 'alertas:lista')


@login_required
def lista_alertas(request):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')

    status = (request.GET.get('status') or 'pendentes').strip().lower()
    modulo = (request.GET.get('modulo') or '').strip().lower()
    nivel = (request.GET.get('nivel') or '').strip().lower()

    qs = _alertas_visiveis(request)
    if status == 'pendentes':
        qs = qs.filter(status__in=[Alerta.Status.ABERTO, Alerta.Status.LIDO])
    elif status in Alerta.Status.values:
        qs = qs.filter(status=status)
    else:
        status = 'pendentes'
        qs = qs.filter(status__in=[Alerta.Status.ABERTO, Alerta.Status.LIDO])

    if modulo in Alerta.Modulo.values:
        qs = qs.filter(modulo=modulo)
    else:
        modulo = ''

    if nivel in Alerta.Nivel.values:
        qs = qs.filter(nivel=nivel)
    else:
        nivel = ''

    alertas = list(qs.order_by('-data_alerta', '-id')[:200])
    return render(
        request,
        'alertas/lista.html',
        {
            'page_title': 'Alertas',
            'alertas': alertas,
            'status_atual': status,
            'modulo_atual': modulo,
            'nivel_atual': nivel,
            'status_choices': Alerta.Status.choices,
            'modulo_choices': Alerta.Modulo.choices,
            'nivel_choices': Alerta.Nivel.choices,
        },
    )


@login_required
@require_POST
def marcar_lido(request, pk):
    alerta = get_object_or_404(_alertas_visiveis(request), pk=pk)
    alerta.marcar_lido()
    messages.success(request, 'Alerta marcado como lido.')
    return _redirect_after_action(request)


@login_required
@require_POST
def resolver(request, pk):
    alerta = get_object_or_404(_alertas_visiveis(request), pk=pk)
    alerta.marcar_resolvido()
    messages.success(request, 'Alerta resolvido.')
    return _redirect_after_action(request)


@login_required
@require_POST
def marcar_todos_lidos(request):
    qs = _alertas_visiveis(request).filter(status=Alerta.Status.ABERTO)
    now = timezone.now()
    qtd = qs.update(status=Alerta.Status.LIDO, lido_em=now, atualizado_em=now)
    if qtd:
        messages.success(request, f'{qtd} alerta(s) marcado(s) como lido(s).')
    else:
        messages.info(request, 'Não havia alertas abertos para marcar.')
    return redirect_empresa(request, 'alertas:lista')
