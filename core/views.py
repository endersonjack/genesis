from django.contrib import messages as django_messages
from django.contrib.messages import get_messages
from django.http import HttpResponse
from django.template.loader import render_to_string


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
