from django.urls import path

from .views import preferencias

urlpatterns = [
    path('preferencias/', preferencias, name='empresa_preferencias'),
]
