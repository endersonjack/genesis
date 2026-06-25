from django.contrib import admin

from .models import NotaAutoadesiva


@admin.register(NotaAutoadesiva)
class NotaAutoadesivaAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'tipo_label', 'autor', 'responsavel', 'concluida', 'criada_em')
    list_filter = ('empresa', 'concluida', 'criada_em')
    search_fields = ('texto', 'autor__username', 'autor__nome_completo', 'responsavel__username', 'responsavel__nome_completo')
    autocomplete_fields = ('empresa', 'autor', 'responsavel')
