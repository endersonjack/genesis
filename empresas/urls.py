from django.urls import path

from core.view_helpers import empresa_scoped

from .views import preferencias

urlpatterns = [
    path('', empresa_scoped(preferencias), name='empresa_preferencias'),
]
