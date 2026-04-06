from django.urls import path

from controles_rh.views.competencias import (
    criar_competencia,
    detalhe_competencia,
    editar_competencia,
    excluir_competencia,
    lista_competencias,
)
from controles_rh.views.home import home_controles_rh
from controles_rh.views.vale_transporte import (
    adicionar_item_vt,
    criar_tabela_vt,
    detalhe_tabela_vt,
    modal_opcoes_criar_tabela_vt,
    editar_item_vt,
    editar_tabela_vt,
    excluir_item_vt,
    excluir_tabela_vt,
    excluir_tabela_vt_legacy_redirect,
    modal_pagamento_item_vt,
    reordenar_itens_vt,
)
from controles_rh.views.cesta_basica import (
    adicionar_item_cesta_basica,
    criar_cesta_basica,
    definir_recebido_item_cesta_basica,
    detalhe_cesta_basica,
    editar_cesta_basica_lista,
    editar_item_cesta_basica,
    excluir_cesta_basica_lista,
    excluir_item_cesta_basica,
    limpar_recebido_cesta_basica,
    receber_todos_cesta_basica,
    reordenar_itens_cesta_basica,
)
from controles_rh.views.cesta_export import (
    exportar_cesta_basica_pdf,
    exportar_cesta_basica_pdf_recibo,
    exportar_cesta_basica_pdf_relatorio,
    exportar_recibo_cesta_individual_por_item,
)
from controles_rh.views.vt_export import exportar_tabela_vt_pdf, exportar_tabela_vt_xlsx

# ROTAS A PARTIR DE /rh/gestao/

app_name = 'controles_rh'

urlpatterns = [
    path('', home_controles_rh, name='home'),

    path('competencias/', lista_competencias, name='lista_competencias'),
    path('competencias/nova/', criar_competencia, name='criar_competencia'),
    path('competencias/<int:ano>/<int:mes>/', detalhe_competencia, name='detalhe_competencia'),
    path('competencias/<int:pk>/editar/', editar_competencia, name='editar_competencia'),
    path('competencias/<int:pk>/excluir/', excluir_competencia, name='excluir_competencia'),

    path(
        'competencias/<int:competencia_pk>/vt/modal-opcoes/',
        modal_opcoes_criar_tabela_vt,
        name='modal_opcoes_criar_tabela_vt',
    ),
    path('competencias/<int:competencia_pk>/vt/nova/', criar_tabela_vt, name='criar_tabela_vt'),
    # Rotas mais específicas antes de `vt/<pk>/` (detalhe).
    path('vt/<int:pk>/exportar/xlsx/', exportar_tabela_vt_xlsx, name='exportar_tabela_vt_xlsx'),
    path('vt/<int:pk>/exportar/pdf/', exportar_tabela_vt_pdf, name='exportar_tabela_vt_pdf'),
    path('vt/<int:pk>/editar/', editar_tabela_vt, name='editar_tabela_vt'),
    # Prefixo `tabela/` evita colisão com outras rotas `vt/...` e deixa a URL explícita.
    path('vt/tabela/<int:pk>/excluir/', excluir_tabela_vt, name='excluir_tabela_vt'),
    path(
        'vt/<int:pk>/excluir/',
        excluir_tabela_vt_legacy_redirect,
        name='excluir_tabela_vt_legacy_redirect',
    ),
    path('vt/<int:pk>/', detalhe_tabela_vt, name='detalhe_tabela_vt'),


    path('vt/<int:tabela_pk>/itens/novo/', adicionar_item_vt, name='adicionar_item_vt'),
    path('vt/<int:tabela_pk>/itens/reordenar/', reordenar_itens_vt, name='reordenar_itens_vt'),
    path('vt/itens/<int:pk>/editar/', editar_item_vt, name='editar_item_vt'),
    path('vt/itens/<int:pk>/pagamento/', modal_pagamento_item_vt, name='modal_pagamento_item_vt'),
    path('vt/itens/<int:pk>/excluir/', excluir_item_vt, name='excluir_item_vt'),

    path('competencias/<int:competencia_pk>/cesta-basica/nova/', criar_cesta_basica, name='criar_cesta_basica'),
    path('cesta-basica/<int:pk>/', detalhe_cesta_basica, name='detalhe_cesta_basica'),
    path('cesta-basica/<int:pk>/editar/', editar_cesta_basica_lista, name='editar_cesta_basica_lista'),
    path('cesta-basica/<int:pk>/excluir/', excluir_cesta_basica_lista, name='excluir_cesta_basica_lista'),
    path(
        'cesta-basica/<int:pk>/exportar/pdf/recibo/',
        exportar_cesta_basica_pdf_recibo,
        name='exportar_cesta_basica_pdf_recibo',
    ),
    path(
        'cesta-basica/<int:pk>/exportar/pdf/relatorio/',
        exportar_cesta_basica_pdf_relatorio,
        name='exportar_cesta_basica_pdf_relatorio',
    ),
    path('cesta-basica/<int:pk>/exportar/pdf/', exportar_cesta_basica_pdf, name='exportar_cesta_basica_pdf'),
    path('cesta-basica/<int:lista_pk>/itens/novo/', adicionar_item_cesta_basica, name='adicionar_item_cesta_basica'),
    path(
        'cesta-basica/<int:lista_pk>/limpar-recebido/',
        limpar_recebido_cesta_basica,
        name='limpar_recebido_cesta_basica',
    ),
    path(
        'cesta-basica/<int:lista_pk>/receber-todos/',
        receber_todos_cesta_basica,
        name='receber_todos_cesta_basica',
    ),
    path('cesta-basica/<int:lista_pk>/itens/reordenar/', reordenar_itens_cesta_basica, name='reordenar_itens_cesta_basica'),
    path('cesta-basica/itens/<int:pk>/editar/', editar_item_cesta_basica, name='editar_item_cesta_basica'),
    path(
        'cesta-basica/itens/<int:pk>/recebido/',
        definir_recebido_item_cesta_basica,
        name='definir_recebido_item_cesta',
    ),
    path(
        'cesta-basica/itens/<int:pk>/recibo/pdf/',
        exportar_recibo_cesta_individual_por_item,
        name='exportar_recibo_cesta_individual_item',
    ),
    path('cesta-basica/itens/<int:pk>/excluir/', excluir_item_cesta_basica, name='excluir_item_cesta_basica'),

]