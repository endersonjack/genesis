from django.urls import path

from core.view_helpers import empresa_scoped

from . import views

app_name = 'fornecedores'

urlpatterns = [
    path('', empresa_scoped(views.lista), name='lista'),
    path('modal/novo/', empresa_scoped(views.modal_novo), name='modal_novo'),
    path(
        'modal/novo-rapido/',
        empresa_scoped(views.modal_novo_rapido),
        name='modal_novo_rapido',
    ),
    path(
        'modal/<int:pk>/excluir/',
        empresa_scoped(views.modal_excluir_confirm),
        name='modal_excluir_confirm',
    ),
    path('modal/<int:pk>/', empresa_scoped(views.modal_editar), name='modal_editar'),
    path('novo/', empresa_scoped(views.criar), name='criar'),
    path(
        '<int:pk>/copiar/modal/',
        empresa_scoped(views.fornecedor_modal_copiar),
        name='modal_copiar',
    ),
    path('<int:pk>/copiar/', empresa_scoped(views.fornecedor_copiar_executar), name='copiar'),
    path('<int:pk>/', empresa_scoped(views.detalhe), name='detalhe'),
    path('<int:pk>/editar/', empresa_scoped(views.editar), name='editar'),
    path('<int:pk>/excluir/', empresa_scoped(views.excluir), name='excluir'),
]
