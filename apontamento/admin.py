from django.contrib import admin

from .models import ApontamentoFalta, ApontamentoObservacaoLocal


@admin.register(ApontamentoFalta)
class ApontamentoFaltaAdmin(admin.ModelAdmin):
    list_display = (
        'funcionario',
        'data',
        'motivo',
        'status',
        'registrado_por',
        'empresa',
        'criado_em',
    )
    list_display_links = ('funcionario',)
    list_filter = ('empresa', 'status', 'data', 'criado_em')
    list_editable = ('status',)
    search_fields = (
        'funcionario__nome',
        'motivo',
        'observacao',
        'registrado_por__username',
        'registrado_por__nome_completo',
    )
    raw_id_fields = ('funcionario', 'registrado_por')


@admin.register(ApontamentoObservacaoLocal)
class ApontamentoObservacaoLocalAdmin(admin.ModelAdmin):
    list_display = ('local', 'data', 'status', 'registrado_por', 'empresa', 'criado_em')
    list_display_links = ('local',)
    list_filter = ('empresa', 'status', 'data', 'criado_em')
    list_editable = ('status',)
    search_fields = ('texto', 'local__nome', 'registrado_por__username')
    raw_id_fields = ('local', 'registrado_por')
