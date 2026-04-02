from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from core.views import genesis_messages_toasts

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('rh/', include('rh.urls')),
    path('rh/gestao/', include('controles_rh.urls')),
    path('', include('dashboard.urls')),

    # Toasts globais para exibir mensagens sem recarregar a página (HTMX/JS)
    path('messages/toasts/', genesis_messages_toasts, name='genesis_messages_toasts'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)