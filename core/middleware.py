from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect

from core.empresa_access import (
    empresa_url_rest,
    modulo_permitido_para_usuario,
    path_permitido_para_so_apontador,
    usuario_e_so_apontador,
)

from usuarios.models import UsuarioEmpresa


class EmpresaAtivaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.empresa_ativa = None
        request.usuario_vinculo_empresa = None
        request.usuario_admin_empresa = False
        request.usuario_apontador = False
        request.usuario_so_apontador = False
        request.usuario_nav_mobile_apontamento = False
        request.usuario_mod_editar_empresas = False
        request.usuario_mod_rh = False
        request.usuario_mod_estoque = False
        request.usuario_mod_financeiro = False
        request.usuario_mod_clientes = False
        request.usuario_mod_fornecedores = False
        request.usuario_mod_locais = False
        request.usuario_mod_obras = False
        request.usuario_mod_auditoria_total = False
        request.usuario_mod_auditoria_sua = False
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        empresa_id = view_kwargs.get('empresa_id')
        if empresa_id is None:
            return None

        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        try:
            vinculo = UsuarioEmpresa.objects.select_related('empresa').get(
                usuario=request.user,
                empresa_id=empresa_id,
                ativo=True,
                empresa__ativa=True,
            )
        except UsuarioEmpresa.DoesNotExist:
            messages.error(
                request,
                'Você não tem acesso a esta empresa ou o vínculo não está ativo.',
            )
            return redirect('selecionar_empresa')

        empresa = vinculo.empresa
        request.empresa_ativa = empresa
        request.usuario_vinculo_empresa = vinculo
        request.usuario_admin_empresa = bool(vinculo.admin_empresa)
        request.usuario_apontador = bool(vinculo.apontador)
        request.usuario_so_apontador = usuario_e_so_apontador(request.user, vinculo)
        request.usuario_mod_editar_empresas = bool(getattr(vinculo, 'editar_empresas', False))
        request.usuario_mod_rh = bool(getattr(vinculo, 'rh', False))
        request.usuario_mod_estoque = bool(getattr(vinculo, 'estoque', False))
        request.usuario_mod_financeiro = bool(getattr(vinculo, 'financeiro', False))
        request.usuario_mod_clientes = bool(getattr(vinculo, 'clientes', False))
        request.usuario_mod_fornecedores = bool(getattr(vinculo, 'fornecedores', False))
        request.usuario_mod_locais = bool(getattr(vinculo, 'locais', False))
        request.usuario_mod_obras = bool(getattr(vinculo, 'obras', False))
        request.usuario_mod_auditoria_total = bool(getattr(vinculo, 'auditoria_total', False))
        request.usuario_mod_auditoria_sua = bool(getattr(vinculo, 'auditoria_sua', False))
        # Mesmo critério do link «Apontamento» no sidebar (apontador / admin empresa / superuser).
        request.usuario_nav_mobile_apontamento = bool(
            request.usuario_so_apontador
            or request.usuario_apontador
            or request.usuario_admin_empresa
            or request.user.is_superuser
        )
        request.session['empresa_id'] = empresa.id

        if request.usuario_so_apontador:
            rest = empresa_url_rest(request.path, empresa_id)
            if not path_permitido_para_so_apontador(rest):
                messages.warning(
                    request,
                    'Seu acesso é limitado ao Apontamento e às telas de locais autorizadas.',
                )
                return redirect(
                    'apontamento:home',
                    empresa_id=empresa_id,
                )
        else:
            # Controle de acesso por módulo (exceto admin empresa/superuser).
            if not (request.usuario_admin_empresa or request.user.is_superuser):
                rest = empresa_url_rest(request.path, empresa_id)
                permitido, msg = modulo_permitido_para_usuario(rest, vinculo)
                if not permitido:
                    messages.error(request, msg)
                    return redirect('dashboard_home', empresa_id=empresa_id)

        return None
