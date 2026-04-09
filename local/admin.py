from django.contrib import admin

from .models import Local


@admin.register(Local)
class LocalAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'endereco', 'latitude', 'longitude', 'atualizado_em')
    list_filter = ('empresa',)
    search_fields = ('nome', 'endereco')
    autocomplete_fields = ('empresa',)
