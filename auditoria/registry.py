from __future__ import annotations

from typing import Any

from django.http import HttpRequest


def registrar_auditoria(
    request: HttpRequest,
    *,
    acao: str,
    resumo: str,
    modulo: str = '',
    detalhes: dict[str, Any] | None = None,
) -> None:
    """
    Grava um evento de auditoria para a empresa ativa e o usuário autenticado.
    Ignora silenciosamente se não houver empresa ativa ou usuário (ex.: comando de gestão).
    """
    empresa = getattr(request, 'empresa_ativa', None)
    user = getattr(request, 'user', None)
    if not empresa or not user or not user.is_authenticated:
        return

    from auditoria.models import RegistroAuditoria

    RegistroAuditoria.objects.create(
        empresa=empresa,
        usuario=user,
        acao=acao,
        modulo=(modulo or '')[:80],
        resumo=(resumo or '')[:255],
        detalhes=detalhes or {},
    )


def audit_rh(
    request: HttpRequest,
    acao: str,
    resumo: str,
    detalhes: dict[str, Any] | None = None,
) -> None:
    """Atalho para módulo RH (`modulo='rh'`)."""
    registrar_auditoria(
        request,
        acao=acao,
        resumo=resumo,
        modulo='rh',
        detalhes=detalhes,
    )


def audit_controles_rh(
    request: HttpRequest,
    acao: str,
    resumo: str,
    detalhes: dict[str, Any] | None = None,
) -> None:
    """Atalho para Controles RH (`modulo='controles_rh'`)."""
    registrar_auditoria(
        request,
        acao=acao,
        resumo=resumo,
        modulo='controles_rh',
        detalhes=detalhes,
    )


def audit_apontamento(
    request: HttpRequest,
    acao: str,
    resumo: str,
    detalhes: dict[str, Any] | None = None,
) -> None:
    """Atalho para Apontamento — faltas e anotações de campo (`modulo='apontamento'`)."""
    registrar_auditoria(
        request,
        acao=acao,
        resumo=resumo,
        modulo='apontamento',
        detalhes=detalhes,
    )
