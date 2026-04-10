from usuarios.models import UsuarioEmpresa

from core import brand_static
from core.modulo_topbar import titulo_modulo_topbar


def modulo_topbar(request):
    return {'modulo_topbar_titulo': titulo_modulo_topbar(request)}


def brand_icons(request):
    """
    Marca Genesis (static): favicon, apple-touch e imagem principal (sidebar, login).
    """
    main_logo = None
    for candidate in ("img/logo.png", "img/pwa-icon.svg"):
        if brand_static.static_exists(candidate):
            main_logo = candidate
            break
    if main_logo is None:
        main_logo = "img/pwa-icon.svg"
    return {
        "brand_main_logo_static": main_logo,
        "brand_favicon": brand_static.favicon_info(),
        "brand_apple_touch_path": brand_static.apple_touch_path(),
    }


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
