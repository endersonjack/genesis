from django.urls import path

from core.view_helpers import empresa_scoped

from . import views

app_name = 'apontamento'

urlpatterns = [
    path('', empresa_scoped(views.home), name='home'),
    path('falta/nova/', empresa_scoped(views.falta_nova), name='falta_nova'),
    path(
        'falta/registros-anteriores/',
        empresa_scoped(views.faltas_anteriores),
        name='faltas_anteriores',
    ),
    path(
        'falta/<int:pk>/editar/',
        empresa_scoped(views.falta_editar),
        name='falta_editar',
    ),
    path(
        'falta/<int:pk>/excluir/',
        empresa_scoped(views.falta_excluir),
        name='falta_excluir',
    ),
    path(
        'observacao/nova/',
        empresa_scoped(views.observacao_nova),
        name='observacao_nova',
    ),
    path(
        'observacao/registros-anteriores/',
        empresa_scoped(views.observacoes_anteriores),
        name='observacoes_anteriores',
    ),
    path(
        'observacao/<int:pk>/editar/',
        empresa_scoped(views.observacao_editar),
        name='observacao_editar',
    ),
    path(
        'observacao/<int:pk>/excluir/',
        empresa_scoped(views.observacao_excluir),
        name='observacao_excluir',
    ),
    path(
        'observacao/<int:observacao_pk>/foto/<int:foto_pk>/excluir/',
        empresa_scoped(views.observacao_foto_excluir),
        name='observacao_foto_excluir',
    ),
    path(
        'busca-funcionarios/',
        empresa_scoped(views.busca_funcionarios),
        name='busca_funcionarios',
    ),
    path(
        'fragment/faltas-hoje/',
        empresa_scoped(views.faltas_hoje_fragment),
        name='faltas_hoje_fragment',
    ),
    path(
        'fragment/observacoes-hoje/',
        empresa_scoped(views.observacoes_hoje_fragment),
        name='observacoes_hoje_fragment',
    ),
    path(
        'falta/<int:pk>/status/',
        empresa_scoped(views.falta_alterar_status),
        name='falta_alterar_status',
    ),
    path(
        'observacao/<int:pk>/status/',
        empresa_scoped(views.observacao_alterar_status),
        name='observacao_alterar_status',
    ),
]
