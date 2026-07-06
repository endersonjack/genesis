from django.contrib import admin

from .models import (
    AlteracaoFolhaControle,
    AlteracaoFolhaLinha,
    AnexoDiversoCompetencia,
    CestaBasicaItem,
    CestaBasicaLista,
    Competencia,
    PagamentoSalarioControle,
    PagamentoSalarioLinha,
    PremiacaoFuncionario,
    ValeTransporteItem,
    ValeTransporteTabela,
)


@admin.register(AnexoDiversoCompetencia)
class AnexoDiversoCompetenciaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'competencia', 'usuario', 'data_criacao')
    list_filter = ('competencia__empresa', 'competencia__ano', 'competencia__mes')
    search_fields = ('nome', 'descricao', 'usuario__username', 'usuario__nome_completo')
    autocomplete_fields = ('competencia', 'usuario')
    ordering = ('-data_criacao', '-id')


@admin.register(AlteracaoFolhaControle)
class AlteracaoFolhaControleAdmin(admin.ModelAdmin):
    list_display = ('id', 'competencia', 'data_geracao')
    list_filter = ('competencia__empresa', 'competencia__ano', 'competencia__mes')
    search_fields = ('competencia__titulo',)
    autocomplete_fields = ('competencia',)
    ordering = ('-data_geracao',)


@admin.register(AlteracaoFolhaLinha)
class AlteracaoFolhaLinhaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'competencia',
        'funcionario',
        'hora_extra',
        'horas_feriado',
        'adicional',
        'descontos',
        'data_atualizacao',
    )
    list_filter = ('competencia__empresa', 'competencia__ano', 'competencia__mes')
    search_fields = ('funcionario__nome',)
    autocomplete_fields = ('competencia', 'funcionario')
    ordering = ('competencia__ano', 'competencia__mes', 'funcionario__nome')


@admin.register(PremiacaoFuncionario)
class PremiacaoFuncionarioAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'competencia',
        'funcionario',
        'premio_atual',
        'premio_anterior',
        'media_premiacao',
        'data_atualizacao',
    )
    list_filter = ('competencia__empresa', 'competencia__ano', 'competencia__mes')
    search_fields = ('funcionario__nome', 'funcionario__cpf')
    autocomplete_fields = ('competencia', 'funcionario')
    ordering = ('competencia__ano', 'competencia__mes', 'funcionario__nome')


@admin.register(PagamentoSalarioControle)
class PagamentoSalarioControleAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome_exibicao', 'competencia', 'data_geracao', 'data_atualizacao')
    list_filter = ('competencia__empresa', 'competencia__ano', 'competencia__mes')
    search_fields = ('nome', 'competencia__titulo')
    autocomplete_fields = ('competencia',)
    ordering = ('-data_geracao',)


@admin.register(PagamentoSalarioLinha)
class PagamentoSalarioLinhaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'controle',
        'funcionario',
        'valor',
        'conta_bancaria_empresa',
        'data_atualizacao',
    )
    list_filter = ('controle__competencia__empresa', 'controle__competencia__ano', 'controle__competencia__mes')
    search_fields = ('funcionario__nome', 'funcionario__cpf', 'conta_bancaria_empresa__nome', 'conta_bancaria_empresa__banco')
    autocomplete_fields = ('controle', 'funcionario', 'conta_bancaria_empresa')
    ordering = ('controle__competencia__ano', 'controle__competencia__mes', 'funcionario__nome')


@admin.register(Competencia)
class CompetenciaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'empresa',
        'referencia',
        'titulo',
        'fechada',
        'vt_calculo_automatico',
        'vt_status_manual',
        'data_criacao',
    )
    list_filter = ('empresa', 'ano', 'mes', 'fechada')
    search_fields = ('titulo', 'empresa__nome')
    ordering = ('-ano', '-mes', '-id')


@admin.register(ValeTransporteTabela)
class ValeTransporteTabelaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'nome',
        'competencia',
        'ativa',
        'fechada',
        'vt_calculo_automatico',
        'vt_status_manual',
        'ordem',
        'data_criacao',
    )
    list_filter = ('competencia__empresa', 'competencia__ano', 'competencia__mes', 'ativa', 'fechada')
    search_fields = ('nome', 'descricao', 'competencia__titulo')
    ordering = ('competencia__ano', 'competencia__mes', 'ordem', 'nome')


@admin.register(CestaBasicaLista)
class CestaBasicaListaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'competencia',
        'titulo',
        'cb_calculo_automatico',
        'cb_status_manual',
        'ativa',
        'data_criacao',
    )
    list_filter = ('competencia__empresa', 'competencia__ano', 'competencia__mes', 'ativa')
    search_fields = ('titulo', 'observacao', 'competencia__titulo')
    ordering = ('competencia__ano', 'competencia__mes', 'id')


@admin.register(CestaBasicaItem)
class CestaBasicaItemAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'nome_exibicao',
        'lista',
        'funcao',
        'lotacao',
        'recebido',
        'data_recebimento',
        'ordem',
        'ativo',
    )
    list_filter = ('lista__competencia__empresa', 'lista__competencia__ano', 'ativo', 'recebido')
    search_fields = ('nome', 'funcao', 'lotacao', 'funcionario__nome')
    ordering = ('lista', 'ordem', 'nome', 'id')


@admin.register(ValeTransporteItem)
class ValeTransporteItemAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'nome_exibicao',
        'tabela',
        'valor_pagar',
        'valor_base',
        'valor_pago',
        'data_pagamento',
        'tipo_pix',
        'ativo',
    )
    list_filter = ('tabela__competencia__empresa', 'tabela__competencia__ano', 'tabela__competencia__mes', 'tipo_pix', 'ativo')
    search_fields = ('nome', 'funcao', 'endereco', 'pix', 'banco', 'funcionario__nome')
    ordering = ('tabela', 'ordem', 'nome', 'id')
