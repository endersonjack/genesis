from django.urls import path

from .views import (
    modal_trocar_empresa,
    pagina_trocar_empresa_legacy,
    selecionar_empresa,
    trocar_empresa,
)

urlpatterns = [
    path('selecionar-empresa/', selecionar_empresa, name='selecionar_empresa'),
    path(
        'trocar-empresa/pagina/',
        pagina_trocar_empresa_legacy,
        name='trocar_empresa_pagina_legacy',
    ),
    path('modal-trocar-empresa/', modal_trocar_empresa, name='modal_trocar_empresa'),
    path('trocar-empresa/', trocar_empresa, name='trocar_empresa'),
]