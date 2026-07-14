from django.db import DatabaseError
from django.db.models import Case, IntegerField, Value, When

from .models import Alerta
from .permissions import filtrar_alertas_permitidos


def alertas_topbar(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}

    empresa = getattr(request, 'empresa_ativa', None)
    if not empresa:
        return {
            'alertas_topbar_qtd': 0,
            'alertas_topbar_recentes': [],
        }

    try:
        qs = (
            Alerta.objects.filter(empresa=empresa, status=Alerta.Status.ABERTO)
            .filter(usuario__isnull=True)
            | Alerta.objects.filter(
                empresa=empresa,
                status=Alerta.Status.ABERTO,
                usuario=request.user,
            )
        )
        qs = (
            filtrar_alertas_permitidos(request, qs)
            .distinct()
            .annotate(
                sem_vencimento=Case(
                    When(data_vencimento__isnull=True, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
            .order_by('sem_vencimento', 'data_vencimento', 'data_alerta', 'id')
        )
        qtd = qs.count()
        resolver_match = getattr(request, 'resolver_match', None)
        return {
            'alertas_topbar_qtd': qtd,
            'alertas_topbar_recentes': list(qs),
            'alertas_topbar_auto_open': (
                qtd > 0
                and getattr(resolver_match, 'view_name', '') == 'rh:dashboard_rh'
            ),
        }
    except DatabaseError:
        return {
            'alertas_topbar_qtd': 0,
            'alertas_topbar_recentes': [],
        }
