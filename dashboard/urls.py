from django.urls import path
from core.view_helpers import empresa_scoped
from .views import home

urlpatterns = [
    path('', empresa_scoped(home), name='dashboard_home'),
]
