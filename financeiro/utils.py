"""Utilitários do app financeiro."""
from empresas.models import Empresa

from .models import Caixa


def garantir_caixa_geral(empresa: Empresa) -> Caixa:
    """Garante existência do caixa geral consolidado da empresa (idempotente)."""
    caixa, _ = Caixa.objects.get_or_create(
        empresa=empresa,
        tipo=Caixa.Tipo.GERAL,
        defaults={'nome': 'Caixa geral', 'ativo': True},
    )
    return caixa
