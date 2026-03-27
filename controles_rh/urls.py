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
    criar_tabela_vt,
    detalhe_tabela_vt,
    editar_tabela_vt,
    excluir_tabela_vt,
)

from controles_rh.views.vale_transporte import (
    criar_tabela_vt,
    detalhe_tabela_vt,
    editar_tabela_vt,
    excluir_tabela_vt,
    adicionar_item_vt,
    editar_item_vt,
    excluir_item_vt,
)

# ROTAS A PARTIR DE /rh/gestao/

app_name = 'controles_rh'

urlpatterns = [
    path('', home_controles_rh, name='home'),

    # path('competencias/', lista_competencias, name='lista_competencias'),
    path('competencias/nova/', criar_competencia, name='criar_competencia'),
    path('competencias/<int:ano>/<int:mes>/', detalhe_competencia, name='detalhe_competencia'),
    path('competencias/<int:pk>/editar/', editar_competencia, name='editar_competencia'),
    path('competencias/<int:pk>/excluir/', excluir_competencia, name='excluir_competencia'),

    path('competencias/<int:competencia_pk>/vt/nova/', criar_tabela_vt, name='criar_tabela_vt'),
    path('vt/<int:pk>/', detalhe_tabela_vt, name='detalhe_tabela_vt'),
    path('vt/<int:pk>/editar/', editar_tabela_vt, name='editar_tabela_vt'),
    path('vt/<int:pk>/excluir/', excluir_tabela_vt, name='excluir_tabela_vt'),


    path('vt/<int:tabela_pk>/itens/novo/', adicionar_item_vt, name='adicionar_item_vt'),
    path('vt/itens/<int:pk>/editar/', editar_item_vt, name='editar_item_vt'),
    path('vt/itens/<int:pk>/excluir/', excluir_item_vt, name='excluir_item_vt'),

]