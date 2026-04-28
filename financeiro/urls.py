from django.urls import path

from core.view_helpers import empresa_scoped

from . import views

app_name = 'financeiro'

urlpatterns = [
    path('', empresa_scoped(views.dashboard), name='dashboard'),
    path('buscar/', empresa_scoped(views.buscar_pagamentos), name='buscar_pagamentos'),
    path(
        'partial/dashboard-cards/',
        empresa_scoped(views.partial_dashboard_cards),
        name='partial_dashboard_cards',
    ),
    path('caixas/', empresa_scoped(views.caixa_lista), name='caixa_lista'),
    path('caixas/novo/', empresa_scoped(views.caixa_novo), name='caixa_novo'),
    path('caixas/<int:pk>/', empresa_scoped(views.caixa_detalhe), name='caixa_detalhe'),
    path(
        'caixas/<int:pk>/editar/',
        empresa_scoped(views.caixa_editar),
        name='caixa_editar',
    ),
    path(
        'caixas/<int:pk>/inativar/',
        empresa_scoped(views.caixa_inativar),
        name='caixa_inativar',
    ),
    path(
        'caixas/<int:pk>/reativar/',
        empresa_scoped(views.caixa_reativar),
        name='caixa_reativar',
    ),
    path(
        'movimentar/',
        empresa_scoped(views.movimentar_caixa),
        name='movimentar_caixa',
    ),
    path(
        'movimentar/pagamento/',
        empresa_scoped(views.movimentar_pagamento),
        name='movimentar_pagamento',
    ),
    path(
        'pagamentos/nf/novo/',
        empresa_scoped(views.pagamento_nf_novo),
        name='pagamento_nf_novo',
    ),
    path(
        'pagamentos/nf/<int:pk>/',
        empresa_scoped(views.pagamento_nf_detalhe),
        name='pagamento_nf_detalhe',
    ),
    path(
        'pagamentos/nf/<int:pk>/editar/',
        empresa_scoped(views.pagamento_nf_editar),
        name='pagamento_nf_editar',
    ),
    path(
        'pagamentos/nf/<int:pk>/pagar-boleto/',
        empresa_scoped(views.pagamento_nf_pagar_boleto),
        name='pagamento_nf_pagar_boleto',
    ),
    path(
        'pagamentos/nf/<int:pk>/excluir/',
        empresa_scoped(views.pagamento_nf_excluir),
        name='pagamento_nf_excluir',
    ),
    path(
        'movimentar/recebimento-avulso/',
        empresa_scoped(views.recebimento_avulso_novo),
        name='recebimento_avulso_novo',
    ),
    path(
        'movimentar/recebimento-medicao/',
        empresa_scoped(views.recebimento_medicao_novo),
        name='recebimento_medicao_novo',
    ),
    path(
        'movimentar/recebimentos/<str:tipo>/<int:pk>/liquidar/',
        empresa_scoped(views.recebimento_liquidar),
        name='recebimento_liquidar',
    ),
    path('categorias/', empresa_scoped(views.categoria_lista), name='categoria_lista'),
    path('categorias/novo/', empresa_scoped(views.categoria_novo), name='categoria_novo'),
    path(
        'categorias/<int:pk>/editar/',
        empresa_scoped(views.categoria_editar),
        name='categoria_editar',
    ),
    path(
        'categorias/<int:pk>/inativar/',
        empresa_scoped(views.categoria_inativar),
        name='categoria_inativar',
    ),
    path(
        'categorias/<int:pk>/reativar/',
        empresa_scoped(views.categoria_reativar),
        name='categoria_reativar',
    ),
]
