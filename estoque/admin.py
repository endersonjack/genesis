from django.contrib import admin

from .models import (
    CategoriaFerramenta,
    CategoriaItem,
    Item,
    ItemImagem,
    RequisicaoEstoque,
    RequisicaoEstoqueItem,
    UnidadeMedida,
)


@admin.register(CategoriaItem)
class CategoriaItemAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'atualizado_em')
    list_filter = ('empresa',)
    search_fields = ('nome',)
    ordering = ('empresa', 'nome')


@admin.register(CategoriaFerramenta)
class CategoriaFerramentaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'atualizado_em')
    list_filter = ('empresa',)
    search_fields = ('nome',)
    ordering = ('empresa', 'nome')


@admin.register(UnidadeMedida)
class UnidadeMedidaAdmin(admin.ModelAdmin):
    list_display = ('abreviada', 'completa', 'empresa', 'atualizado_em')
    list_filter = ('empresa',)
    search_fields = ('abreviada', 'completa')
    ordering = ('empresa', 'abreviada')


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = (
        'descricao',
        'categoria',
        'unidade_medida',
        'quantidade_estoque',
        'ativo',
        'preco',
        'empresa',
        'atualizado_em',
    )
    list_filter = ('empresa', 'categoria', 'ativo')
    search_fields = ('descricao', 'marca')
    ordering = ('empresa', 'descricao')
    autocomplete_fields = ('categoria', 'unidade_medida', 'fornecedor')


class RequisicaoEstoqueItemInline(admin.TabularInline):
    model = RequisicaoEstoqueItem
    extra = 0
    autocomplete_fields = ('item',)
    readonly_fields = ('pk',)


@admin.register(RequisicaoEstoque)
class RequisicaoEstoqueAdmin(admin.ModelAdmin):
    list_display = ('pk', 'empresa', 'status', 'solicitante', 'criado_em')
    list_filter = ('empresa', 'status')
    search_fields = ('pk', 'solicitante__nome')
    autocomplete_fields = ('empresa', 'solicitante', 'local', 'obra', 'almoxarife')
    readonly_fields = ('criado_em', 'atualizado_em')
    inlines = (RequisicaoEstoqueItemInline,)


@admin.register(ItemImagem)
class ItemImagemAdmin(admin.ModelAdmin):
    list_display = ('item', 'ordem', 'atualizado_em')
    list_filter = ('item__empresa',)
    ordering = ('item', 'ordem')
