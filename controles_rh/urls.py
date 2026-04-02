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
    editar_item_vt,
    editar_tabela_vt,
    excluir_item_vt,
    excluir_tabela_vt,
    modal_pagamento_item_vt,
    reordenar_itens_vt,
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

    path('competencias/<int:competencia_pk>/vt/nova/', criar_tabela_vt, name='criar_tabela_vt'),
    path('vt/<int:pk>/', detalhe_tabela_vt, name='detalhe_tabela_vt'),
    path('vt/<int:pk>/exportar/xlsx/', exportar_tabela_vt_xlsx, name='exportar_tabela_vt_xlsx'),
    path('vt/<int:pk>/exportar/pdf/', exportar_tabela_vt_pdf, name='exportar_tabela_vt_pdf'),
    path('vt/<int:pk>/editar/', editar_tabela_vt, name='editar_tabela_vt'),
    path('vt/<int:pk>/excluir/', excluir_tabela_vt, name='excluir_tabela_vt'),


    path('vt/<int:tabela_pk>/itens/novo/', adicionar_item_vt, name='adicionar_item_vt'),
    path('vt/<int:tabela_pk>/itens/reordenar/', reordenar_itens_vt, name='reordenar_itens_vt'),
    path('vt/itens/<int:pk>/editar/', editar_item_vt, name='editar_item_vt'),
    path('vt/itens/<int:pk>/pagamento/', modal_pagamento_item_vt, name='modal_pagamento_item_vt'),
    path('vt/itens/<int:pk>/excluir/', excluir_item_vt, name='excluir_item_vt'),

]