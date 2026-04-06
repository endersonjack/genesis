from django.urls import path

from .views import pagina_trocar_empresa

urlpatterns = [
    path(
        'trocar-empresa/pagina/',
        pagina_trocar_empresa,
        name='trocar_empresa_pagina',
    ),
]
