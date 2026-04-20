from django.contrib import admin

from .models import (
    CategoriaFerramenta,
    CategoriaItem,
    Cautela,
    Entrega_Cautela,
    Ferramenta,
    FerramentaImagem,
    Item,
    ItemImagem,
    ListaCompraEstoque,
    ListaCompraEstoqueItem,
    MotivoDevolucaoCautela,
    RequisicaoEstoque,
    RequisicaoEstoqueItem,
    SituacaoFerramentasPosDevolucao,
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


@admin.register(Ferramenta)
class FerramentaAdmin(admin.ModelAdmin):
    list_display = (
        'descricao',
        'categoria',
        'codigo_numeracao',
        'ativo',
        'preco',
        'empresa',
        'atualizado_em',
    )
    list_filter = ('empresa', 'categoria', 'ativo')
    search_fields = ('descricao', 'marca', 'codigo_numeracao', 'cor')
    ordering = ('empresa', 'descricao')
    autocomplete_fields = ('categoria', 'fornecedor')


@admin.register(FerramentaImagem)
class FerramentaImagemAdmin(admin.ModelAdmin):
    list_display = ('ferramenta', 'ordem', 'padrao', 'atualizado_em')
    list_filter = ('ferramenta__empresa',)
    ordering = ('ferramenta', 'ordem')


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


class ListaCompraEstoqueItemInline(admin.TabularInline):
    model = ListaCompraEstoqueItem
    extra = 0
    autocomplete_fields = ('item',)


@admin.register(ListaCompraEstoque)
class ListaCompraEstoqueAdmin(admin.ModelAdmin):
    list_display = ('pk', 'nome', 'empresa', 'data_pedido', 'status', 'criado_em')
    list_filter = ('empresa', 'status')
    search_fields = ('nome', 'observacoes')
    autocomplete_fields = ('empresa', 'criado_por')
    readonly_fields = ('criado_em', 'atualizado_em')
    inlines = (ListaCompraEstoqueItemInline,)


@admin.register(ItemImagem)
class ItemImagemAdmin(admin.ModelAdmin):
    list_display = ('item', 'ordem', 'padrao', 'atualizado_em')
    list_filter = ('item__empresa',)
    ordering = ('item', 'ordem')


class Entrega_CautelaInline(admin.TabularInline):
    model = Entrega_Cautela
    extra = 0
    autocomplete_fields = (
        'cautela',
        'motivo',
        'situacao_ferramentas',
    )


@admin.register(Cautela)
class CautelaAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'empresa',
        'funcionario',
        'situacao',
        'entrega',
        'data_inicio_cautela',
        'data_fim',
        'criado_em',
    )
    list_filter = ('empresa', 'situacao', 'entrega')
    search_fields = ('funcionario__nome',)
    autocomplete_fields = ('empresa', 'funcionario', 'almoxarife', 'local', 'obra')
    readonly_fields = ('criado_em', 'atualizado_em')
    inlines = (Entrega_CautelaInline,)


@admin.register(MotivoDevolucaoCautela)
class MotivoDevolucaoCautelaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'ativo', 'atualizado_em')
    list_filter = ('empresa', 'ativo')
    search_fields = ('nome',)
    ordering = ('empresa', 'nome')


@admin.register(SituacaoFerramentasPosDevolucao)
class SituacaoFerramentasPosDevolucaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'ativo', 'atualizado_em')
    list_filter = ('empresa', 'ativo')
    search_fields = ('nome',)
    ordering = ('empresa', 'nome')


@admin.register(Entrega_Cautela)
class Entrega_CautelaAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'cautela',
        'tipo',
        'data_entrega',
        'motivo',
        'situacao_ferramentas',
        'criado_em',
    )
    list_filter = ('tipo',)
    search_fields = ('cautela__funcionario__nome',)
    autocomplete_fields = (
        'cautela',
        'motivo',
        'situacao_ferramentas',
    )
    filter_horizontal = ('ferramentas_devolvidas',)
    readonly_fields = ('criado_em', 'atualizado_em')
