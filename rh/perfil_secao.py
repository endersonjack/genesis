"""
Links para o perfil do funcionário com ?secao= e opcionalmente ?saude= (subaba),
para abrir direto na seção relacionada a um tipo de evento (dashboard/calendário).
"""
from __future__ import annotations

from urllib.parse import urlencode

from core.urlutils import reverse_empresa

# tipo de evento (dashboard/calendário) -> (secao menu, subaba saúde ou None)
TIPO_PARA_SECAO: dict[str, tuple[str, str | None]] = {
    "admissao": ("admissao", None),
    "experiencia_45": ("admissao", None),
    "inicio_prorrogacao": ("admissao", None),
    "fim_prorrogacao": ("admissao", None),
    "inicio_aviso": ("demissao", None),
    "fim_aviso": ("demissao", None),
    "demissao": ("demissao", None),
    "ferias_inicio": ("ferias", None),
    "ferias_volta": ("ferias", None),
    "afastamento": ("afastamentos", None),
    "retorno_afastamento": ("afastamentos", None),
    "aso": ("saude", "aso"),
    "ultimo_exame": ("saude", "aso"),
    "alerta_exame": ("saude", "aso"),
    "renovacao_exame": ("saude", "aso"),
    "exame": ("saude", "aso"),
    "pcmso": ("saude", "pcmso"),
    "lembrete": ("outros", None),
    "aniversario": ("pessoais", None),
}


def perfil_funcionario_url_por_tipo(request, funcionario_pk: int, tipo_evento: str) -> str:
    """URL absoluta no site para o perfil, com query de seção quando aplicável."""
    base = reverse_empresa(
        request,
        "rh:detalhes_funcionario",
        kwargs={"pk": funcionario_pk},
    )
    return anexar_secao_na_url(base, tipo_evento)


def anexar_secao_na_url(url: str, tipo_evento: str) -> str:
    """Acrescenta ?secao= / &saude= a uma URL de perfil (ou retorna url se não houver mapeamento)."""
    pair = TIPO_PARA_SECAO.get(tipo_evento)
    if not pair:
        return url
    secao, saude = pair
    query: dict[str, str] = {}
    if secao:
        query["secao"] = secao
    if saude:
        query["saude"] = saude
    if not query:
        return url
    joiner = "&" if "?" in url else "?"
    return f"{url}{joiner}{urlencode(query)}"
