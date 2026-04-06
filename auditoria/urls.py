from django.urls import path

from core.view_helpers import empresa_scoped

from .views import lista_auditoria

app_name = 'auditoria'

urlpatterns = [
    path('', empresa_scoped(lista_auditoria), name='lista'),
]
