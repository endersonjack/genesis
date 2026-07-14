from django.urls import path

from core.view_helpers import empresa_scoped

from . import views

app_name = 'alertas'

urlpatterns = [
    path('', empresa_scoped(views.lista_alertas), name='lista'),
    path('<int:pk>/marcar-lido/', empresa_scoped(views.marcar_lido), name='marcar_lido'),
    path('<int:pk>/resolver/', empresa_scoped(views.resolver), name='resolver'),
    path('marcar-todos-lidos/', empresa_scoped(views.marcar_todos_lidos), name='marcar_todos_lidos'),
]
