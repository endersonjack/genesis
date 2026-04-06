from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect

from usuarios.models import UsuarioEmpresa


class EmpresaAtivaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.empresa_ativa = None
        request.usuario_admin_empresa = False
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
        request.usuario_admin_empresa = bool(vinculo.admin_empresa)
        request.session['empresa_id'] = empresa.id
        return None
