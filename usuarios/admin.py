from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, UsuarioEmpresa


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Informações adicionais', {
            'fields': ('nome_completo', 'telefone', 'foto'),
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
                'fields': (
                    'ativo',
                    'admin_empresa',
                    'editar_empresas',
                    'rh',
                    'estoque',
                    'financeiro',
                    'apontador',
                    'clientes',
                    'fornecedores',
                    'locais',
                    'obras',
                    'auditoria_total',
                    'auditoria_sua',
                ),
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
    list_display = (
        'usuario',
        'empresa',
        'ativo',
        'admin_empresa',
        'apontador',
        'rh',
        'estoque',
        'financeiro',
        'clientes',
        'fornecedores',
        'locais',
        'obras',
        'auditoria_total',
        'auditoria_sua',
        'criado_em',
    )
    list_filter = (
        'ativo',
        'admin_empresa',
        'apontador',
        'rh',
        'estoque',
        'financeiro',
        'clientes',
        'fornecedores',
        'locais',
        'obras',
        'auditoria_total',
        'auditoria_sua',
        'empresa',
    )
    search_fields = ('usuario__username', 'usuario__nome_completo', 'empresa__razao_social')