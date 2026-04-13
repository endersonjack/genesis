from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'tipo',
        'cpf_cnpj',
        'empresa',
        'telefone',
        'email',
        'atualizado_em',
    )
    list_filter = ('empresa', 'tipo')
    search_fields = ('nome', 'razao_social', 'email', 'telefone', 'cpf_cnpj')
    ordering = ('empresa', 'nome')
