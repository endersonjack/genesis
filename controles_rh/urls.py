from django.urls import path

from core.view_helpers import empresa_scoped

from controles_rh.views.af_export import exportar_alteracao_folha_pdf
from controles_rh.views.alteracao_folha import (
    alteracao_folha_competencia,
    excluir_alteracao_folha_competencia,
    gerar_alteracao_folha_competencia,
    modal_alteracao_folha_linha,
)
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
    path('', empresa_scoped(home_controles_rh), name='home'),

    path('competencias/', empresa_scoped(lista_competencias), name='lista_competencias'),
    path('competencias/nova/', empresa_scoped(criar_competencia), name='criar_competencia'),
    path('competencias/<int:ano>/<int:mes>/', empresa_scoped(detalhe_competencia), name='detalhe_competencia'),
    path(
        'competencias/<int:competencia_pk>/alteracao-folha/gerar/',
        empresa_scoped(gerar_alteracao_folha_competencia),
        name='gerar_alteracao_folha_competencia',
    ),
    path(
        'competencias/<int:competencia_pk>/alteracao-folha/excluir/',
        empresa_scoped(excluir_alteracao_folha_competencia),
        name='excluir_alteracao_folha_competencia',
    ),
    path(
        'competencias/<int:competencia_pk>/alteracao-folha/linha/<int:linha_pk>/modal/',
        empresa_scoped(modal_alteracao_folha_linha),
        name='modal_alteracao_folha_linha',
    ),
    path(
        'competencias/<int:competencia_pk>/alteracao-folha/exportar/pdf/',
        empresa_scoped(exportar_alteracao_folha_pdf),
        name='exportar_alteracao_folha_pdf',
    ),
    path(
        'competencias/<int:competencia_pk>/alteracao-folha/',
        empresa_scoped(alteracao_folha_competencia),
        name='alteracao_folha_competencia',
    ),
    path('competencias/<int:pk>/editar/', empresa_scoped(editar_competencia), name='editar_competencia'),
    path('competencias/<int:pk>/excluir/', empresa_scoped(excluir_competencia), name='excluir_competencia'),

    path(
        'competencias/<int:competencia_pk>/vt/modal-opcoes/',
        empresa_scoped(modal_opcoes_criar_tabela_vt),
        name='modal_opcoes_criar_tabela_vt',
    ),
    path('competencias/<int:competencia_pk>/vt/nova/', empresa_scoped(criar_tabela_vt), name='criar_tabela_vt'),
    # Rotas mais específicas antes de `vt/<pk>/` (detalhe).
    path('vt/<int:pk>/exportar/xlsx/', empresa_scoped(exportar_tabela_vt_xlsx), name='exportar_tabela_vt_xlsx'),
    path('vt/<int:pk>/exportar/pdf/', empresa_scoped(exportar_tabela_vt_pdf), name='exportar_tabela_vt_pdf'),
    path('vt/<int:pk>/editar/', empresa_scoped(editar_tabela_vt), name='editar_tabela_vt'),
    # Prefixo `tabela/` evita colisão com outras rotas `vt/...` e deixa a URL explícita.
    path('vt/tabela/<int:pk>/excluir/', empresa_scoped(excluir_tabela_vt), name='excluir_tabela_vt'),
    path(
        'vt/<int:pk>/excluir/',
        empresa_scoped(excluir_tabela_vt_legacy_redirect),
        name='excluir_tabela_vt_legacy_redirect',
    ),
    path('vt/<int:pk>/', empresa_scoped(detalhe_tabela_vt), name='detalhe_tabela_vt'),


    path('vt/<int:tabela_pk>/itens/novo/', empresa_scoped(adicionar_item_vt), name='adicionar_item_vt'),
    path('vt/<int:tabela_pk>/itens/reordenar/', empresa_scoped(reordenar_itens_vt), name='reordenar_itens_vt'),
    path('vt/itens/<int:pk>/editar/', empresa_scoped(editar_item_vt), name='editar_item_vt'),
    path('vt/itens/<int:pk>/pagamento/', empresa_scoped(modal_pagamento_item_vt), name='modal_pagamento_item_vt'),
    path('vt/itens/<int:pk>/excluir/', empresa_scoped(excluir_item_vt), name='excluir_item_vt'),

    path('competencias/<int:competencia_pk>/cesta-basica/nova/', empresa_scoped(criar_cesta_basica), name='criar_cesta_basica'),
    path('cesta-basica/<int:pk>/', empresa_scoped(detalhe_cesta_basica), name='detalhe_cesta_basica'),
    path('cesta-basica/<int:pk>/editar/', empresa_scoped(editar_cesta_basica_lista), name='editar_cesta_basica_lista'),
    path('cesta-basica/<int:pk>/excluir/', empresa_scoped(excluir_cesta_basica_lista), name='excluir_cesta_basica_lista'),
    path(
        'cesta-basica/<int:pk>/exportar/pdf/recibo/',
        empresa_scoped(exportar_cesta_basica_pdf_recibo),
        name='exportar_cesta_basica_pdf_recibo',
    ),
    path(
        'cesta-basica/<int:pk>/exportar/pdf/relatorio/',
        empresa_scoped(exportar_cesta_basica_pdf_relatorio),
        name='exportar_cesta_basica_pdf_relatorio',
    ),
    path('cesta-basica/<int:pk>/exportar/pdf/', empresa_scoped(exportar_cesta_basica_pdf), name='exportar_cesta_basica_pdf'),
    path('cesta-basica/<int:lista_pk>/itens/novo/', empresa_scoped(adicionar_item_cesta_basica), name='adicionar_item_cesta_basica'),
    path(
        'cesta-basica/<int:lista_pk>/limpar-recebido/',
        empresa_scoped(limpar_recebido_cesta_basica),
        name='limpar_recebido_cesta_basica',
    ),
    path(
        'cesta-basica/<int:lista_pk>/receber-todos/',
        empresa_scoped(receber_todos_cesta_basica),
        name='receber_todos_cesta_basica',
    ),
    path('cesta-basica/<int:lista_pk>/itens/reordenar/', empresa_scoped(reordenar_itens_cesta_basica), name='reordenar_itens_cesta_basica'),
    path('cesta-basica/itens/<int:pk>/editar/', empresa_scoped(editar_item_cesta_basica), name='editar_item_cesta_basica'),
    path(
        'cesta-basica/itens/<int:pk>/recebido/',
        empresa_scoped(definir_recebido_item_cesta_basica),
        name='definir_recebido_item_cesta',
    ),
    path(
        'cesta-basica/itens/<int:pk>/recibo/pdf/',
        empresa_scoped(exportar_recibo_cesta_individual_por_item),
        name='exportar_recibo_cesta_individual_item',
    ),
    path('cesta-basica/itens/<int:pk>/excluir/', empresa_scoped(excluir_item_cesta_basica), name='excluir_item_cesta_basica'),

]