from django.urls import path
from .views import selecionar_empresa

urlpatterns = [
    path('selecionar-empresa/', selecionar_empresa, name='selecionar_empresa'),
]