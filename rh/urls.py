from django.urls import path
from . import views

app_name = 'rh'

urlpatterns = [
    path('', views.dashboard_rh, name='dashboard_rh'),
    path('funcionarios/', views.lista_funcionarios, name='lista_funcionarios'),
    path('funcionarios/novo/', views.criar_funcionario, name='criar_funcionario'),
    path('funcionarios/<int:pk>/', views.detalhar_funcionario, name='detalhar_funcionario'),
    path('funcionarios/<int:pk>/editar/', views.editar_funcionario, name='editar_funcionario'),
    path('funcionarios/<int:pk>/excluir/', views.excluir_funcionario, name='excluir_funcionario'),


    path('cargos/', views.lista_cargos, name='lista_cargos'),
    path('cargos/novo/', views.criar_cargo, name='criar_cargo'),
    path('cargos/<int:pk>/editar/', views.editar_cargo, name='editar_cargo'),
    path('cargos/<int:pk>/excluir/', views.excluir_cargo, name='excluir_cargo'),

    path('lotacoes/', views.lista_lotacoes, name='lista_lotacoes'),
    path('lotacoes/nova/', views.criar_lotacao, name='criar_lotacao'),
    path('lotacoes/<int:pk>/editar/', views.editar_lotacao, name='editar_lotacao'),
    path('lotacoes/<int:pk>/excluir/', views.excluir_lotacao, name='excluir_lotacao'),

]