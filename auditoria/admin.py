from django.contrib import admin

from .models import RegistroAuditoria


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser

    list_display = (
        'criado_em',
        'empresa',
        'usuario',
        'acao',
        'modulo',
        'resumo',
    )
    list_filter = ('acao', 'modulo', 'empresa')
    search_fields = ('resumo', 'usuario__username', 'usuario__nome_completo')
    readonly_fields = (
        'empresa',
        'usuario',
        'criado_em',
        'acao',
        'modulo',
        'resumo',
        'detalhes',
    )
    date_hierarchy = 'criado_em'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
