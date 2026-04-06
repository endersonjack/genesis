from django.urls import path

from core.view_helpers import empresa_scoped

from . import views

app_name = 'local'

urlpatterns = [
    path('', empresa_scoped(views.lista_locais), name='lista'),
    path('criar/', empresa_scoped(views.local_criar), name='criar'),
    path('<int:pk>/editar/', empresa_scoped(views.local_editar), name='editar'),
    path('<int:pk>/excluir/', empresa_scoped(views.local_excluir), name='excluir'),
]
