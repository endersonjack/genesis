from django.contrib import admin
from django.urls import include, path, re_path
from django.conf import settings
from django.views.static import serve

from core.views import genesis_messages_toasts, home_root_redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('messages/toasts/', genesis_messages_toasts, name='genesis_messages_toasts'),
    path(
        'empresa/<int:empresa_id>/',
        include([
            path('', include('dashboard.urls')),
            path('preferencias/', include('empresas.urls')),
            path('local/', include('local.urls')),
            path('rh/gestao/', include('controles_rh.urls')),
            path('rh/', include('rh.urls')),
            path('usuarios/', include('usuarios.urls_empresa')),
        ]),
    ),
    path('', home_root_redirect, name='home_root'),
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
