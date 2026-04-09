from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, UsuarioEmpresa


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Informações adicionais', {
            'fields': ('nome_completo', 'telefone'),
        }),
    )


@admin.register(UsuarioEmpresa)
class UsuarioEmpresaAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            None,
            {
                'fields': ('usuario', 'empresa'),
            },
        ),
        (
            'Acesso nesta empresa',
            {
                'fields': ('ativo', 'admin_empresa', 'apontador'),
                'description': 'Apontador: acesso ao módulo Apontamento (celular/campo) para esta empresa.',
            },
        ),
        (
            'Auditoria',
            {
                'fields': ('criado_em',),
            },
        ),
    )
    readonly_fields = ('criado_em',)
    list_display = ('usuario', 'empresa', 'ativo', 'admin_empresa', 'apontador', 'criado_em')
    list_filter = ('ativo', 'admin_empresa', 'apontador', 'empresa')
    search_fields = ('usuario__username', 'usuario__nome_completo', 'empresa__razao_social')