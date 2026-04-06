from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from auditoria.models import RegistroAuditoria


@login_required
def home(request):
    context = {}
    empresa = getattr(request, 'empresa_ativa', None)
    if empresa:
        pode_ver_todos = bool(
            getattr(request, 'usuario_admin_empresa', False) or request.user.is_superuser
        )
        qs = (
            RegistroAuditoria.objects.filter(empresa=empresa)
            .select_related('usuario')
            .order_by('-criado_em')
        )
        if not pode_ver_todos:
            qs = qs.filter(usuario=request.user)
        context['ultimas_auditoria'] = list(qs[:20])
        context['auditoria_resumo_admin'] = pode_ver_todos
    return render(request, 'dashboard/home.html', context)
