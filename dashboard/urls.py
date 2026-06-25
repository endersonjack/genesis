from django.urls import path
from core.view_helpers import empresa_scoped
from .views import alternar_nota, criar_nota, editar_nota, excluir_nota, home, notas_concluidas

urlpatterns = [
    path('', empresa_scoped(home), name='dashboard_home'),
    path('notas/concluidas/', empresa_scoped(notas_concluidas), name='dashboard_notas_concluidas'),
    path('notas/nova/', empresa_scoped(criar_nota), name='dashboard_criar_nota'),
    path('notas/<int:pk>/editar/', empresa_scoped(editar_nota), name='dashboard_editar_nota'),
    path('notas/<int:pk>/alternar/', empresa_scoped(alternar_nota), name='dashboard_alternar_nota'),
    path('notas/<int:pk>/excluir/', empresa_scoped(excluir_nota), name='dashboard_excluir_nota'),
]
