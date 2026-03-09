from empresas.models import Empresa
from usuarios.models import UsuarioEmpresa


class EmpresaAtivaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.empresa_ativa = None
        request.usuario_admin_empresa = False

        empresa_id = request.session.get('empresa_id')

        if request.user.is_authenticated and empresa_id:
            try:
                empresa = Empresa.objects.get(id=empresa_id, ativa=True)
                request.empresa_ativa = empresa

                request.usuario_admin_empresa = UsuarioEmpresa.objects.filter(
                    usuario=request.user,
                    empresa=empresa,
                    ativo=True,
                    admin_empresa=True
                ).exists()

            except Empresa.DoesNotExist:
                request.empresa_ativa = None
                request.usuario_admin_empresa = False

        response = self.get_response(request)
        return response