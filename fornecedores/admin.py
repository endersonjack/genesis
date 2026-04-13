from django.contrib import admin

from .models import CategoriaFornecedor, Fornecedor


@admin.register(CategoriaFornecedor)
class CategoriaFornecedorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'atualizado_em')
    list_filter = ('empresa',)
    search_fields = ('nome',)
    ordering = ('empresa', 'nome')


@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'cpf_cnpj', 'empresa', 'categoria', 'atualizado_em')
    list_filter = ('empresa', 'tipo', 'categoria')
    search_fields = ('nome', 'razao_social', 'cpf_cnpj', 'email')
    ordering = ('empresa', 'nome')
