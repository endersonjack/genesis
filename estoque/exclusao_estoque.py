"""Detecção de vínculos e arquivamento lógico ao «excluir» item/ferramenta usados em histórico."""
from __future__ import annotations

from django.db.models import Q

from .models import (
    Cautela,
    Ferramenta,
    Item,
    ListaCompraEstoque,
    ListaCompraEstoqueItem,
    RequisicaoEstoque,
    RequisicaoEstoqueItem,
)

SUFIXO_EXCLUIDO = ' (EXCLUÍDO)'


def descricao_com_sufixo_excluido(descricao: str, max_length: int) -> str:
    base = (descricao or '').strip()
    if not base:
        base = '—'
    low = base.lower()
    suf = SUFIXO_EXCLUIDO.lower()
    if low.endswith(suf):
        return base[:max_length]
    room = max_length - len(SUFIXO_EXCLUIDO)
    trimmed = base[: max(0, room)].rstrip()
    return (trimmed + SUFIXO_EXCLUIDO)[:max_length]


def requisicoes_com_item(item: Item) -> list:
    pks = (
        RequisicaoEstoqueItem.objects.filter(item=item)
        .values_list('requisicao_id', flat=True)
        .distinct()
    )
    return list(
        RequisicaoEstoque.objects.filter(pk__in=pks).order_by('-criado_em', '-pk')
    )


def listas_compra_com_item(item: Item) -> list:
    pks = (
        ListaCompraEstoqueItem.objects.filter(item=item)
        .values_list('lista_id', flat=True)
        .distinct()
    )
    return list(
        ListaCompraEstoque.objects.filter(pk__in=pks).order_by('-data_pedido', '-pk')
    )


def item_precisa_arquivar(item: Item) -> bool:
    return bool(requisicoes_com_item(item) or listas_compra_com_item(item))


def cautelas_com_ferramenta(ferramenta: Ferramenta):
    return (
        Cautela.objects.filter(
            empresa=ferramenta.empresa_id,
        )
        .filter(
            Q(ferramentas=ferramenta) | Q(entregas__ferramentas_devolvidas=ferramenta)
        )
        .distinct()
        .select_related('funcionario')
        .order_by('-data_inicio_cautela', '-pk')
    )


def ferramenta_precisa_arquivar(ferramenta: Ferramenta) -> bool:
    return cautelas_com_ferramenta(ferramenta).exists()
