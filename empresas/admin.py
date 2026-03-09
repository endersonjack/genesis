from django.contrib import admin
from .models import Empresa
from .forms import EmpresaForm


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    form = EmpresaForm
    list_display = ('razao_social', 'nome_fantasia', 'cnpj', 'cor_tema', 'ativa')
    search_fields = ('razao_social', 'nome_fantasia', 'cnpj')
    list_filter = ('ativa',)