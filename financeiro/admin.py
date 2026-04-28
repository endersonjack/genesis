from django.contrib import admin

from core.moeda_fmt import format_decimal_br_moeda

from .models import Caixa, MovimentoCaixa, RecebimentoAvulso, RecebimentoMedicao


@admin.register(Caixa)
class CaixaAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'tipo',
        'obra',
        'empresa',
        'ativo',
        'saldo_formatado',
    )
    list_filter = ('tipo', 'ativo', 'empresa')
    search_fields = ('nome', 'obra__nome')
    raw_id_fields = ('obra',)
    readonly_fields = ('saldo_atual_readonly',)

    fieldsets = (
        (None, {'fields': ('empresa', 'tipo', 'nome', 'obra', 'ativo')}),
        ('Saldo', {'fields': ('saldo_atual_readonly',)}),
    )

    @admin.display(description='Saldo atual')
    def saldo_formatado(self, obj: Caixa):
        v = obj.saldo_atual()
        return f'R$ {format_decimal_br_moeda(v)}'

    @admin.display(description='Saldo (calculado)')
    def saldo_atual_readonly(self, obj: Caixa):
        if not obj.pk:
            return '—'
        return self.saldo_formatado(obj)

    def save_model(self, request, obj, form, change):
        obj.full_clean()
        super().save_model(request, obj, form, change)


@admin.register(MovimentoCaixa)
class MovimentoCaixaAdmin(admin.ModelAdmin):
    list_display = (
        'data',
        'natureza',
        'valor',
        'caixa',
        'categoria_origem',
        'meio_pagamento',
        'descricao_curta',
        'empresa',
    )
    list_filter = ('natureza', 'categoria_origem', 'meio_pagamento', 'data', 'empresa')
    search_fields = ('descricao', 'observacao')
    raw_id_fields = ('caixa',)
    date_hierarchy = 'data'
    ordering = ('-data', '-pk')

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'empresa',
                    'caixa',
                    'natureza',
                    'categoria_origem',
                    'meio_pagamento',
                    'valor',
                    'data',
                    'descricao',
                    'observacao',
                )
            },
        ),
    )

    @admin.display(description='Descrição')
    def descricao_curta(self, obj: MovimentoCaixa):
        return (obj.descricao[:60] + '…') if len(obj.descricao) > 60 else obj.descricao

    def save_model(self, request, obj, form, change):
        if obj.caixa_id and not obj.empresa_id:
            obj.empresa_id = obj.caixa.empresa_id
        obj.full_clean()
        super().save_model(request, obj, form, change)


@admin.register(RecebimentoAvulso)
class RecebimentoAvulsoAdmin(admin.ModelAdmin):
    list_display = ('pk', 'cliente', 'movimento', 'criado_em')
    list_filter = ('criado_em',)
    search_fields = ('cliente__nome', 'movimento__descricao')
    raw_id_fields = ('movimento', 'cliente')


@admin.register(RecebimentoMedicao)
class RecebimentoMedicaoAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'cliente',
        'obra',
        'medicao_numero',
        'nota_fiscal_numero',
        'movimento',
        'criado_em',
    )
    list_filter = ('criado_em',)
    search_fields = (
        'medicao_numero',
        'nota_fiscal_numero',
        'cliente__nome',
        'obra__nome',
    )
    raw_id_fields = ('movimento', 'cliente', 'obra')
