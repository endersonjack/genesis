from django.contrib import admin
from .models import (
    Cargo,
    TipoContrato,
    Lotacao,
    Banco,
    Funcionario,
    Dependente,
)


class DependenteInline(admin.TabularInline):
    model = Dependente
    extra = 1


@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'cpf',
        'empresa',
        'matricula',
        'cargo',
        'lotacao',
        'situacao_atual',
        'data_admissao',
    )
    search_fields = (
        'nome',
        'cpf',
        'rg',
        'matricula',
    )
    list_filter = (
        'empresa',
        'situacao_atual',
        'cargo',
        'lotacao',
        'tipo_contrato',
        'analfabeto',
    )
    autocomplete_fields = (
        'empresa',
        'cargo',
        'lotacao',
        'tipo_contrato',
        'banco',
    )
    inlines = [DependenteInline]

    fieldsets = (
        ('Controle', {
            'fields': (
                'empresa',
                'id_erp',
                'matricula',
                'foto',
            )
        }),
        ('Dados Pessoais', {
            'fields': (
                'nome',
                'cpf',
                'rg',
                'cnh',
                'categoria_cnh',
                'nacionalidade',
                'data_nascimento',
                'endereco_completo',
                ('telefone_1', 'telefone_2'),
                ('estado_civil', 'sexo'),
                ('nome_mae', 'nome_pai'),
            )
        }),
        ('Dados Contratuais', {
            'fields': (
                'tipo_contrato',
                'data_admissao',
                ('inicio_prorrogacao', 'fim_prorrogacao'),
                'situacao_atual',
                ('inicio_afastamento', 'fim_afastamento'),
                ('data_demissao', 'tipo_demissao'),
                ('cargo'),
                'lotacao',
                ('salario', 'adicional'),
                ('data_ultimo_exame', 'responsavel'),
            )
        }),
        ('Dados Bancários', {
            'fields': (
                'banco',
                ('agencia', 'operacao'),
                ('tipo_conta', 'numero_conta'),
                ('tipo_pix', 'pix'),
            )
        }),
        ('Outras Informações', {
            'fields': (
                'e_social',
                'analfabeto',
                'observacoes',
            )
        }),
    )


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa')
    search_fields = ('nome',)
    list_filter = ('empresa',)


@admin.register(TipoContrato)
class TipoContratoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa')
    search_fields = ('nome',)
    list_filter = ('empresa',)


@admin.register(Lotacao)
class LotacaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa')
    search_fields = ('nome',)
    list_filter = ('empresa',)


@admin.register(Banco)
class BancoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nome')
    search_fields = ('codigo', 'nome')