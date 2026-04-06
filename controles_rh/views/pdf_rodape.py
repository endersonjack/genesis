"""
Rodapé padrão para PDFs: usuário que imprimiu, data/hora e nome do sistema (discreto).
"""
from typing import List
from xml.sax.saxutils import escape as xml_escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer

NOME_SISTEMA = 'Gênesis ERP'


def _nome_usuario_impressao(request) -> str:
    if request is None:
        return '—'
    user = getattr(request, 'user', None)
    if user is None:
        return '—'
    if getattr(user, 'is_authenticated', False):
        full = (user.get_full_name() or '').strip()
        if full:
            return full
        un = (getattr(user, 'username', '') or '').strip()
        return un or '—'
    return '—'


def flowables_rodape_impressao(
    request,
    styles,
    *,
    space_before_mm: float = 2.5,
) -> List:
    """Usuário · dd/mm/aaaa hh:mm · Gênesis ERP, alinhado à direita, texto pequeno e cinza."""
    agora = timezone.localtime(timezone.now())
    emitido = agora.strftime('%d/%m/%Y %H:%M')
    nome = _nome_usuario_impressao(request)
    linha = f'{nome} · {emitido} · {NOME_SISTEMA}'
    rodape_style = ParagraphStyle(
        'genesis_rodape_impressao',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6,
        leading=7.5,
        spaceBefore=0,
        spaceAfter=0,
        textColor=colors.HexColor('#94a3b8'),
        alignment=2,
    )
    return [
        Spacer(1, space_before_mm * mm),
        Paragraph(xml_escape(linha), rodape_style),
    ]
