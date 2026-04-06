from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string


@login_required
def home_root_redirect(request):
    """Raiz `/`: envia para o dashboard da empresa na sessão ou para seleção."""
    empresa_id = request.session.get('empresa_id')
    if empresa_id:
        return redirect('dashboard_home', empresa_id=empresa_id)
    return redirect('selecionar_empresa')


def genesis_messages_toasts(request):
    """
    Devolve as mensagens do Django como HTML (toasts do Bootstrap) para uso via HTMX/JS.

    Importante: ao iterar as mensagens com `get_messages(request)`, elas são consumidas,
    evitando reaparecer depois.
    """
    msgs = list(get_messages(request))
    if not msgs:
        return HttpResponse('', content_type='text/html')

    html = render_to_string(
        'includes/genesis_messages_toasts_inner.html',
        {'messages': msgs},
        request=request,
    )
    return HttpResponse(html, content_type='text/html')
