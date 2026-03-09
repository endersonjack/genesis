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
    list_display = ('usuario', 'empresa', 'ativo', 'admin_empresa', 'criado_em')
    list_filter = ('ativo', 'admin_empresa', 'empresa')
    search_fields = ('usuario__username', 'usuario__nome_completo', 'empresa__razao_social')