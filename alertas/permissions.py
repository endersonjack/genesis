from .models import Alerta


MODULO_ALERTA_PARA_FLAG_REQUEST = {
    Alerta.Modulo.RH: 'usuario_mod_rh',
    Alerta.Modulo.FINANCEIRO: 'usuario_mod_financeiro',
    Alerta.Modulo.ESTOQUE: 'usuario_mod_estoque',
    Alerta.Modulo.CLIENTES: 'usuario_mod_clientes',
    Alerta.Modulo.FORNECEDORES: 'usuario_mod_fornecedores',
    Alerta.Modulo.LOCAL: 'usuario_mod_locais',
    Alerta.Modulo.OBRAS: 'usuario_mod_obras',
    Alerta.Modulo.APONTAMENTO: 'usuario_apontador',
}


MODULO_ALERTA_PARA_FLAG_VINCULO = {
    Alerta.Modulo.RH: 'rh',
    Alerta.Modulo.FINANCEIRO: 'financeiro',
    Alerta.Modulo.ESTOQUE: 'estoque',
    Alerta.Modulo.CLIENTES: 'clientes',
    Alerta.Modulo.FORNECEDORES: 'fornecedores',
    Alerta.Modulo.LOCAL: 'locais',
    Alerta.Modulo.OBRAS: 'obras',
    Alerta.Modulo.APONTAMENTO: 'apontador',
}


def usuario_e_admin_alertas(request):
    user = getattr(request, 'user', None)
    return bool(
        getattr(user, 'is_superuser', False)
        or getattr(request, 'usuario_admin_empresa', False)
    )


def modulos_alerta_permitidos(request):
    if usuario_e_admin_alertas(request):
        return list(Alerta.Modulo.values)

    vinculo = getattr(request, 'usuario_vinculo_empresa', None)
    modulos = []
    for modulo, request_flag in MODULO_ALERTA_PARA_FLAG_REQUEST.items():
        vinculo_flag = MODULO_ALERTA_PARA_FLAG_VINCULO.get(modulo)
        if getattr(request, request_flag, False) or (
            vinculo is not None and vinculo_flag and getattr(vinculo, vinculo_flag, False)
        ):
            modulos.append(modulo)
    return modulos


def filtrar_alertas_permitidos(request, qs):
    if usuario_e_admin_alertas(request):
        return qs
    modulos = modulos_alerta_permitidos(request)
    if not modulos:
        return qs.none()
    return qs.filter(modulo__in=modulos)
