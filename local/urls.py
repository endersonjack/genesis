from django.urls import path

from . import views

app_name = 'local'

urlpatterns = [
    path('', views.lista_locais, name='lista'),
    path('criar/', views.local_criar, name='criar'),
    path('<int:pk>/editar/', views.local_editar, name='editar'),
    path('<int:pk>/excluir/', views.local_excluir, name='excluir'),
]
