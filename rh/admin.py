from django.contrib import admin
from .models import (
    Cargo,
    TipoContrato,
    Lotacao,
    Banco,
    Funcionario,
    Dependente,
    FeriasFuncionario,
    AfastamentoFuncionario,
    ASOFuncionario,
    CertificadoFuncionario,
    PCMSOFuncionario,
    AtestadoLicencaFuncionario,
    OcorrenciaSaudeFuncionario,
)


class DependenteInline(admin.TabularInline):
    model = Dependente
    extra = 1


class FeriasFuncionarioInline(admin.TabularInline):
    model = FeriasFuncionario
    extra = 1


class AfastamentoFuncionarioInline(admin.TabularInline):
    model = AfastamentoFuncionario
    extra = 1


class ASOFuncionarioInline(admin.TabularInline):
    model = ASOFuncionario
    extra = 1


class CertificadoFuncionarioInline(admin.TabularInline):
    model = CertificadoFuncionario
    extra = 1


class PCMSOFuncionarioInline(admin.TabularInline):
    model = PCMSOFuncionario
    extra = 1


class AtestadoLicencaFuncionarioInline(admin.TabularInline):
    model = AtestadoLicencaFuncionario
    extra = 1


class OcorrenciaSaudeFuncionarioInline(admin.TabularInline):
    model = OcorrenciaSaudeFuncionario
    extra = 1


@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'cpf',
        'pis',
        'empresa',
        'matricula',
        'cargo',
        'lotacao',
        'situacao_atual',
        'data_admissao',
        'data_demissao',
    )
    search_fields = (
        'nome',
        'cpf',
        'pis',
        'rg',
        'matricula',
    )
    list_filter = (
        'empresa',
        'situacao_atual',
        'cargo',
        'lotacao',
        'tipo_contrato',
        'contribuinte_sindical',
        'recebe_vale_transporte',
        'analfabeto',
    )
    autocomplete_fields = (
        'empresa',
        'cargo',
        'lotacao',
        'tipo_contrato',
        'banco',
    )
    inlines = [
        DependenteInline,
        FeriasFuncionarioInline,
        AfastamentoFuncionarioInline,
        ASOFuncionarioInline,
        CertificadoFuncionarioInline,
        PCMSOFuncionarioInline,
        AtestadoLicencaFuncionarioInline,
        OcorrenciaSaudeFuncionarioInline,
    ]

    fieldsets = (
        ('Controle', {
            'fields': (
                'empresa',
                'matricula',
                'foto',
            )
        }),
        ('Dados Pessoais', {
            'fields': (
                'nome',
                ('cpf', 'pis'),
                ('rg', 'cnh'),
                'categoria_cnh',
                'nacionalidade',
                'data_nascimento',
                'endereco_completo',
                ('telefone_1', 'telefone_2'),
                ('estado_civil', 'sexo'),
                ('nome_mae', 'nome_pai'),
            )
        }),
        ('Admissão', {
            'fields': (
                'tipo_contrato',
                ('data_admissao', 'situacao_atual'),
                ('inicio_prorrogacao', 'fim_prorrogacao'),
                ('cargo', 'lotacao'),
                ('salario', 'adicional'),
                ('recebe_vale_transporte', 'valor_vale_transporte'),
                'contribuinte_sindical',
                ('data_ultimo_exame', 'responsavel'),
            )
        }),
        ('Demissão', {
            'fields': (
                ('tipo_demissao', 'data_demissao'),
                'tipo_aviso',
                ('data_inicio_aviso', 'data_fim_aviso'),
                'anexo_aviso',
                'precisa_exame_demissional',
                'rescisao_assinada',
                'observacoes_demissao',
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


@admin.register(FeriasFuncionario)
class FeriasFuncionarioAdmin(admin.ModelAdmin):
    list_display = (
        'funcionario',
        'periodo_aquisitivo_inicio',
        'periodo_aquisitivo_fim',
        'gozo_inicio',
        'gozo_fim',
        'teve_abono_pecuniario',
    )
    search_fields = ('funcionario__nome', 'funcionario__cpf')
    list_filter = ('teve_abono_pecuniario',)


@admin.register(AfastamentoFuncionario)
class AfastamentoFuncionarioAdmin(admin.ModelAdmin):
    list_display = (
        'funcionario',
        'tipo',
        'data_afastamento',
        'previsao_retorno',
    )
    search_fields = ('funcionario__nome', 'funcionario__cpf')
    list_filter = ('tipo',)


@admin.register(ASOFuncionario)
class ASOFuncionarioAdmin(admin.ModelAdmin):
    list_display = ('funcionario', 'tipo', 'data')
    search_fields = ('funcionario__nome', 'funcionario__cpf')
    list_filter = ('tipo', 'data')


@admin.register(CertificadoFuncionario)
class CertificadoFuncionarioAdmin(admin.ModelAdmin):
    list_display = ('funcionario', 'tipo', 'data')
    search_fields = ('funcionario__nome', 'funcionario__cpf', 'tipo')
    list_filter = ('data',)


@admin.register(PCMSOFuncionario)
class PCMSOFuncionarioAdmin(admin.ModelAdmin):
    list_display = ('funcionario', 'data_vencimento')
    search_fields = ('funcionario__nome', 'funcionario__cpf')
    list_filter = ('data_vencimento',)


@admin.register(AtestadoLicencaFuncionario)
class AtestadoLicencaFuncionarioAdmin(admin.ModelAdmin):
    list_display = (
        'funcionario',
        'tipo',
        'data',
        'periodo_inicio',
        'periodo_fim',
    )
    search_fields = ('funcionario__nome', 'funcionario__cpf')
    list_filter = ('tipo', 'data')


@admin.register(OcorrenciaSaudeFuncionario)
class OcorrenciaSaudeFuncionarioAdmin(admin.ModelAdmin):
    list_display = ('funcionario', 'tipo', 'origem', 'data')
    search_fields = ('funcionario__nome', 'funcionario__cpf', 'descricao')
    list_filter = ('tipo', 'origem', 'data')