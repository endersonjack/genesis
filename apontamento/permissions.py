"""Quem pode ver/editar status de faltas e observações de apontamento no painel RH."""

from django.http import HttpRequest


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
