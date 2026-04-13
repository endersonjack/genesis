from django.contrib import admin

from .models import Obra


@admin.register(Obra)
class ObraAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'contratante',
        'empresa',
        'data_inicio',
        'data_fim',
        'atualizado_em',
    )
    list_filter = ('empresa',)
    search_fields = ('nome', 'objeto', 'endereco', 'cno', 'contratante__nome')
    autocomplete_fields = ('contratante', 'empresa')
    ordering = ('empresa', 'nome')
