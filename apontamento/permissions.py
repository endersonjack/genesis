"""Quem pode ver/editar status de faltas e observações de apontamento no painel RH."""

from django.http import HttpRequest


def usuario_apontamento_ve_registros_de_todos(request: HttpRequest) -> bool:
    """
    Superusuário ou administrador da empresa: mesmas telas dos apontadores,
    mas com listagens e totais de toda a equipe (não só os próprios registros).
    """
    if not request.user.is_authenticated:
        return False
    if request.user.is_superuser:
        return True
    return bool(getattr(request, 'usuario_admin_empresa', False))


def usuario_rh_pode_gerir_status_apontamento(request: HttpRequest) -> bool:
    """
    Qualquer utilizador com acesso ao módulo RH da empresa (não exclusivamente
    apontador de campo, que não usa o dashboard RH completo).
    """
    if not request.user.is_authenticated:
        return False
    if getattr(request, 'usuario_so_apontador', False):
        return False
    return getattr(request, 'empresa_ativa', None) is not None
