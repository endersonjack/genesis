from django.contrib import admin
from django.db.models import Count

from .models import ApontamentoFalta, ApontamentoObservacaoFoto, ApontamentoObservacaoLocal


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


class ApontamentoObservacaoFotoInline(admin.TabularInline):
    model = ApontamentoObservacaoFoto
    extra = 0


@admin.register(ApontamentoObservacaoLocal)
class ApontamentoObservacaoLocalAdmin(admin.ModelAdmin):
    inlines = (ApontamentoObservacaoFotoInline,)
    list_display = ('local', 'data', 'status', 'registrado_por', 'empresa', 'criado_em', 'qtd_fotos')
    list_display_links = ('local',)
    list_filter = ('empresa', 'status', 'data', 'criado_em')
    list_editable = ('status',)
    search_fields = ('texto', 'local__nome', 'registrado_por__username')
    raw_id_fields = ('local', 'registrado_por')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_qtd_fotos=Count('fotos'))

    @admin.display(description='Fotos')
    def qtd_fotos(self, obj):
        return obj._qtd_fotos
