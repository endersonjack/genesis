"""QR Code interno para itens de estoque (leitor 2D)."""
import logging
import re
from io import BytesIO

# Texto codificado no QR. Formato atual usa hífen (evita ':' no modo teclado ABNT → 'Ç').
# Formato legado com ':' continua aceite no parse (+ normalização de Ç).
QR_PAYLOAD_PREFIX = 'GENESIS-ESTQ'
QR_PAYLOAD_PREFIX_FERR = 'GENESIS-FERR'
_PAYLOAD_RE_DASH = re.compile(
    rf'^{re.escape(QR_PAYLOAD_PREFIX)}-(?P<empresa>\d+)-(?P<item>\d+)\s*$',
    re.IGNORECASE | re.ASCII,
)
_PAYLOAD_RE_COLON = re.compile(
    rf'^{re.escape(QR_PAYLOAD_PREFIX)}:(?P<empresa>\d+):(?P<item>\d+)\s*$',
    re.IGNORECASE | re.ASCII,
)
_PAYLOAD_FERR_DASH = re.compile(
    rf'^{re.escape(QR_PAYLOAD_PREFIX_FERR)}-(?P<empresa>\d+)-(?P<ferramenta>\d+)\s*$',
    re.IGNORECASE | re.ASCII,
)
_PAYLOAD_FERR_COLON = re.compile(
    rf'^{re.escape(QR_PAYLOAD_PREFIX_FERR)}:(?P<empresa>\d+):(?P<ferramenta>\d+)\s*$',
    re.IGNORECASE | re.ASCII,
)

logger = logging.getLogger(__name__)


def _normalize_wedge_qr_string(s: str) -> str:
    """
    Leitor em modo teclado com layout PT-BR (ABNT): o caractere ':' costuma
    ser enviado como 'Ç' ou 'ç', quebrando o parse.
    O payload real só usa ASCII; não há ambiguidade em substituir.
    """
    return s.replace('Ç', ':').replace('ç', ':')


def build_item_qr_payload(empresa_pk: int, item_pk: int) -> str:
    return f'{QR_PAYLOAD_PREFIX}-{int(empresa_pk)}-{int(item_pk)}'


def build_ferramenta_qr_payload(empresa_pk: int, ferramenta_pk: int) -> str:
    return f'{QR_PAYLOAD_PREFIX_FERR}-{int(empresa_pk)}-{int(ferramenta_pk)}'


def parse_item_qr_payload(raw: str):
    """
    Retorna (empresa_pk, item_pk) ou None se inválido.
    Aceita string com espaços extras nas pontas.

    Formatos:
    - Atual: GENESIS-ESTQ-<empresa>-<item> (recomendado; sem dois-pontos)
    - Legado: GENESIS-ESTQ:<empresa>:<item> (e variação com Ç no lugar de :)
    """
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None

    m = _PAYLOAD_RE_DASH.match(s)
    if m:
        return int(m.group('empresa')), int(m.group('item'))

    s_colon = _normalize_wedge_qr_string(s)
    m = _PAYLOAD_RE_COLON.match(s_colon)
    if m:
        return int(m.group('empresa')), int(m.group('item'))

    return None


def parse_ferramenta_qr_payload(raw: str):
    """
    Retorna (empresa_pk, ferramenta_pk) ou None se inválido.
    Mesma convenção de hífen / dois-pontos (e Ç) do payload de item.
    """
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None

    m = _PAYLOAD_FERR_DASH.match(s)
    if m:
        return int(m.group('empresa')), int(m.group('ferramenta'))

    s_colon = _normalize_wedge_qr_string(s)
    m = _PAYLOAD_FERR_COLON.match(s_colon)
    if m:
        return int(m.group('empresa')), int(m.group('ferramenta'))

    return None


def generate_qr_png_bytes(payload: str) -> bytes:
    """
    PNG via Segno (sem depender de Pillow no fluxo de geração).
    Evita falhas silenciosas com combinações qrcode + Pillow 10+.

    - micro=False: Segno, por omissão, usa Micro QR para textos curtos (só 1 quadrado de
      alinhamento). Leitores 2D industriais esperam QR Code Model 2 (3 quadrados nos cantos).
    - border=4: zona de silêncio mínima recomendada (ISO 18004).
    - scale maior: módulos mais nítidos em tela / etiqueta.
    - contraste explícito (#000 / #fff).
    """
    import segno

    buf = BytesIO()
    segno.make(payload, error='q', micro=False).save(
        buf,
        kind='png',
        scale=10,
        border=4,
        dark='#000000',
        light='#ffffff',
    )
    return buf.getvalue()


def attach_auto_qrcode_to_item(item) -> tuple[bool, str | None]:
    """
    Gera PNG do QR com o payload padrão e grava em item.qrcode_imagem.

    Retorna (sucesso, mensagem_curta_erro) — a mensagem é para logs / DEBUG.
    """
    from django.core.files.base import ContentFile

    if not item.pk:
        return False, 'item_sem_pk'

    try:
        payload = build_item_qr_payload(item.empresa_id, item.pk)
        data = generate_qr_png_bytes(payload)
    except Exception as exc:
        logger.exception(
            'estoque.qr_item: falha ao gerar PNG (item_id=%s)', item.pk
        )
        return False, str(exc)

    try:
        if item.qrcode_imagem:
            item.qrcode_imagem.delete(save=False)

        item.qrcode_imagem.save(
            'qrcode.png',
            ContentFile(data),
            save=False,
        )
        item.save(update_fields=['qrcode_imagem'])
    except Exception as exc:
        logger.exception(
            'estoque.qr_item: falha ao gravar qrcode_imagem (item_id=%s)',
            item.pk,
        )
        return False, str(exc)

    return True, None


def attach_auto_qrcode_to_ferramenta(ferramenta) -> tuple[bool, str | None]:
    """Gera PNG do QR e grava em ferramenta.qrcode_imagem."""
    from django.core.files.base import ContentFile

    if not ferramenta.pk:
        return False, 'ferramenta_sem_pk'

    try:
        payload = build_ferramenta_qr_payload(ferramenta.empresa_id, ferramenta.pk)
        data = generate_qr_png_bytes(payload)
    except Exception as exc:
        logger.exception(
            'estoque.qr_item: falha ao gerar PNG (ferramenta_id=%s)', ferramenta.pk
        )
        return False, str(exc)

    try:
        if ferramenta.qrcode_imagem:
            ferramenta.qrcode_imagem.delete(save=False)

        ferramenta.qrcode_imagem.save(
            'qrcode.png',
            ContentFile(data),
            save=False,
        )
        ferramenta.save(update_fields=['qrcode_imagem'])
    except Exception as exc:
        logger.exception(
            'estoque.qr_item: falha ao gravar qrcode_imagem (ferramenta_id=%s)',
            ferramenta.pk,
        )
        return False, str(exc)

    return True, None
