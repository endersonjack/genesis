"""
Helpers HTMX para modais na página de detalhes do funcionário (toasts + secção).
"""

import json


def hx_trigger_secao_modal(secao: str, mensagem: str) -> str:
    """
    Fecha o modal de secção, reabre a secção correta e mostra toast (genesisClientToast).
    """
    return json.dumps(
        {
            "closeSectionModal": True,
            "openSection": {"section": secao},
            "genesisClientToast": {"message": mensagem, "variant": "success"},
        },
        ensure_ascii=False,
    )
