from django.contrib import admin

from .models import Competencia, ValeTransporteTabela, ValeTransporteItem


@admin.register(Competencia)
class CompetenciaAdmin(admin.ModelAdmin):
    list_display = ('id', 'empresa', 'referencia', 'titulo', 'fechada', 'data_criacao')
    list_filter = ('empresa', 'ano', 'mes', 'fechada')
    search_fields = ('titulo', 'empresa__nome')
    ordering = ('-ano', '-mes', '-id')


@admin.register(ValeTransporteTabela)
class ValeTransporteTabelaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'competencia', 'ativa', 'fechada', 'ordem', 'data_criacao')
    list_filter = ('competencia__empresa', 'competencia__ano', 'competencia__mes', 'ativa', 'fechada')
    search_fields = ('nome', 'descricao', 'competencia__titulo')
    ordering = ('competencia__ano', 'competencia__mes', 'ordem', 'nome')


@admin.register(ValeTransporteItem)
class ValeTransporteItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome_exibicao', 'tabela', 'valor_pagar', 'tipo_pix', 'ativo')
    list_filter = ('tabela__competencia__empresa', 'tabela__competencia__ano', 'tabela__competencia__mes', 'tipo_pix', 'ativo')
    search_fields = ('nome', 'funcao', 'endereco', 'pix', 'banco', 'funcionario__nome')
    ordering = ('tabela', 'ordem', 'nome', 'id')