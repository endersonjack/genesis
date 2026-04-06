from django.contrib import admin
from django.urls import include, path, re_path
from django.conf import settings
from django.views.static import serve

from core.views import genesis_messages_toasts

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('empresa/', include('empresas.urls')),
    path('local/', include('local.urls')),
    # Mais específico antes de `rh/`, para `/rh/gestao/` não depender do include genérico de `rh/`.
    path('rh/gestao/', include('controles_rh.urls')),
    path('rh/', include('rh.urls')),
    path('', include('dashboard.urls')),

    # Toasts globais para exibir mensagens sem recarregar a página (HTMX/JS)
    path('messages/toasts/', genesis_messages_toasts, name='genesis_messages_toasts'),
]

# Em DEBUG=False o helper static() não registra rotas; sem isso /media/ dá 404 (ex.: Railway).
# Em produção, prefira volume persistente em MEDIA_ROOT ou storage em objeto (S3/R2).
urlpatterns += [
    re_path(
        r'^media/(?P<path>.*)$',
        serve,
        {'document_root': settings.MEDIA_ROOT},
    ),
]