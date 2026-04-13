from django.urls import path

from core.view_helpers import empresa_scoped

from . import views

app_name = 'local'

urlpatterns = [
    path('', empresa_scoped(views.lista_locais), name='lista'),
    path(
        '<int:pk>/copiar/modal/',
        empresa_scoped(views.local_modal_copiar),
        name='modal_copiar',
    ),
    path('<int:pk>/copiar/', empresa_scoped(views.local_copiar_executar), name='copiar'),
    path('<int:pk>/', empresa_scoped(views.local_detalhe), name='detalhe'),
    path('novo/', empresa_scoped(views.local_criar_page), name='criar_page'),
    path('<int:pk>/editar/pagina/', empresa_scoped(views.local_editar_page), name='editar_page'),
    path('<int:pk>/excluir/pagina/', empresa_scoped(views.local_excluir_page), name='excluir_page'),
    path('criar/', empresa_scoped(views.local_criar), name='criar'),
    path('<int:pk>/editar/', empresa_scoped(views.local_editar), name='editar'),
    path('<int:pk>/excluir/', empresa_scoped(views.local_excluir), name='excluir'),
]
