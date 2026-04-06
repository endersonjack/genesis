from usuarios.models import UsuarioEmpresa


def usuario_empresas(request):
    """
    Quantidade de empresas ativas às quais o utilizador tem acesso.
    Usado no topbar para ocultar o botão de troca quando só há uma empresa.
    """
    if not request.user.is_authenticated:
        return {
            'usuario_qtd_empresas_acesso': 0,
            'usuario_mostrar_troca_empresa': False,
        }
    qtd = UsuarioEmpresa.objects.filter(
        usuario=request.user,
        ativo=True,
        empresa__ativa=True,
    ).count()
    return {
        'usuario_qtd_empresas_acesso': qtd,
        'usuario_mostrar_troca_empresa': qtd > 1,
    }
