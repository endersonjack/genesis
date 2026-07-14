from django.contrib import admin

from .models import Alerta


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = (
        'titulo',
        'empresa',
        'usuario',
        'modulo',
        'nivel',
        'status',
        'data_alerta',
        'data_vencimento',
    )
    list_filter = ('empresa', 'modulo', 'nivel', 'status', 'data_alerta')
    search_fields = ('titulo', 'descricao', 'categoria', 'chave')
    autocomplete_fields = ('empresa', 'usuario', 'criado_por')
    raw_id_fields = ('content_type',)
    readonly_fields = ('criado_em', 'atualizado_em', 'lido_em', 'resolvido_em')
