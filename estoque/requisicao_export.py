"""PDF da requisição de estoque — cabeçalho alinhado ao padrão RH (ReportLab + logo)."""

from __future__ import annotations

from io import BytesIO
from typing import List, Optional
from xml.sax.saxutils import escape as xml_escape

from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from controles_rh.views.cesta_export import (
    _celula_placeholder_logo_mm,
    _empresa_logo_flowable,
    _nome_empresa_pdf,
    _unlink_temp_logo_paths,
)

from .models import RequisicaoEstoque
from .requisicao_qty_fmt import fmt_quantidade_requisicao


class _LinhaCorteEntreVias(Flowable):
    """Tracejado com rótulo central entre as duas vias."""

    def __init__(self, width: float):
        super().__init__()
        self.width = width
        self.height = 5 * mm

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

    def draw(self):
        canv = self.canv
        canv.saveState()
        cy = 2.5 * mm
        canv.setStrokeColor(colors.HexColor('#94a3b8'))
        canv.setLineWidth(0.65)
        canv.setDash(2, 2)
        label = 'Corte aqui'
        canv.setFont('Helvetica', 8)
        lw = canv.stringWidth(label, 'Helvetica', 8)
        gap = lw + 14
        xc = self.width / 2
        x_left_end = xc - gap / 2
        x_right_start = xc + gap / 2
        canv.line(0, cy, max(0, x_left_end), cy)
        canv.line(min(self.width, x_right_start), cy, self.width, cy)
        canv.setDash()
        canv.setFillColor(colors.HexColor('#64748b'))
        canv.drawCentredString(xc, cy - 2.2, label)
        canv.restoreState()


def _header_html_requisicao(empresa) -> str:
    nome = _nome_empresa_pdf(empresa)
    bits = [f'<b>{xml_escape(nome)}</b>']
    razao = (empresa.razao_social or '').strip()
    if razao and razao.upper() != (nome or '').upper():
        bits.append(f'<font size="8" color="#64748b">{xml_escape(razao)}</font>')
    cnpj = (getattr(empresa, 'cnpj', None) or '').strip()
    if cnpj:
        bits.append(xml_escape(f'CNPJ: {cnpj}'))
    tel = (getattr(empresa, 'telefone', None) or '').strip()
    if tel:
        bits.append(xml_escape(f'Tel: {tel}'))
    email = (getattr(empresa, 'email', None) or '').strip()
    if email:
        bits.append(xml_escape(f'E-mail: {email}'))
    return '<br/>'.join(bits)


def _tabela_cabecalho_empresa(
    empresa,
    styles,
    temp_paths: Optional[List[str]],
    largura_total,
):
    """Logo + dados da empresa; `largura_total` limita a coluna esquerda do topo da via."""
    hdr_style = ParagraphStyle(
        'req_hdr_emp',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        alignment=0,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=0,
        spaceBefore=0,
    )
    p = Paragraph(_header_html_requisicao(empresa), hdr_style)
    logo_w_mm = 34
    logo_h_mm = 24
    logo_w = logo_w_mm * mm
    gap_esq = 3 * mm
    text_w = max(10 * mm, largura_total - logo_w - gap_esq)
    logo_img = _empresa_logo_flowable(
        empresa,
        max_w_mm=logo_w_mm,
        max_h_mm=logo_h_mm,
        temp_paths=temp_paths,
    )
    col_esq = logo_img if logo_img else _celula_placeholder_logo_mm(logo_w_mm, logo_h_mm)
    tbl = Table([[col_esq, p]], colWidths=[logo_w, text_w])
    tbl.setStyle(
        TableStyle(
            [
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('ALIGN', (1, 0), (1, 0), 'LEFT'),
                ('LEFTPADDING', (0, 0), (0, 0), 0),
                ('LEFTPADDING', (1, 0), (1, 0), gap_esq),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]
        )
    )
    return tbl


def _story_via(
    *,
    empresa,
    requisicao,
    itens,
    via_label: str,
    doc: SimpleDocTemplate,
    styles,
    temp_paths: Optional[List[str]],
):
    story: list = []
    tw = doc.width
    left_w = tw * 0.62
    right_w = tw - left_w

    left_tbl = _tabela_cabecalho_empresa(
        empresa,
        styles,
        temp_paths,
        left_w,
    )

    if requisicao.criado_em:
        data_txt = timezone.localtime(requisicao.criado_em).strftime('%d/%m/%Y %H:%M')
    else:
        data_txt = '—'

    sub_r = ParagraphStyle(
        'req_via_lbl_r',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#64748b'),
        spaceBefore=0,
        spaceAfter=2 * mm,
        letterSpacing=0.6,
        alignment=TA_RIGHT,
    )
    tit_r = ParagraphStyle(
        'req_tit_r',
        parent=styles['Normal'],
        fontSize=13,
        leading=16,
        fontName='Helvetica-Bold',
        spaceAfter=1 * mm,
        alignment=TA_RIGHT,
    )
    meta_r = ParagraphStyle(
        'req_meta_r',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#475569'),
        alignment=TA_RIGHT,
    )
    right_rows = [
        [Paragraph(xml_escape(via_label.upper()), sub_r)],
        [Paragraph(xml_escape(f'Requisição nº {requisicao.pk}'), tit_r)],
        [Paragraph(xml_escape(f'Emitida em {data_txt}'), meta_r)],
    ]
    if requisicao.status == RequisicaoEstoque.Status.CANCELADA:
        right_rows.append(
            [
                Paragraph(
                    '<b><font color="#842029">CANCELADA — documento informativo.</font></b>',
                    meta_r,
                )
            ]
        )
    right_tbl = Table(right_rows, colWidths=[right_w])
    right_tbl.setStyle(
        TableStyle(
            [
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]
        )
    )
    top_tbl = Table([[left_tbl, right_tbl]], colWidths=[left_w, right_w])
    top_tbl.setStyle(
        TableStyle(
            [
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                (
                    'LINEBELOW',
                    (0, 0),
                    (-1, 0),
                    0.5,
                    colors.HexColor('#e2e8f0'),
                ),
            ]
        )
    )
    story.append(top_tbl)
    story.append(Spacer(1, 4 * mm))

    sol = str(requisicao.solicitante) if requisicao.solicitante_id else '—'
    funcao = '—'
    if requisicao.solicitante_id and requisicao.solicitante:
        cg = getattr(requisicao.solicitante, 'cargo', None)
        if cg is not None:
            funcao = (cg.nome or '').strip() or '—'
    alm = '—'
    if requisicao.almoxarife_id:
        u = requisicao.almoxarife
        alm = (u.nome_completo or u.username or '—') if u else '—'
    loc = str(requisicao.local) if requisicao.local_id else '—'
    obr = str(requisicao.obra) if requisicao.obra_id else '—'

    lab_st = ParagraphStyle(
        'req_lab',
        parent=styles['Normal'],
        fontSize=7,
        leading=9,
        textColor=colors.HexColor('#64748b'),
    )
    val_st = ParagraphStyle(
        'req_val',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        fontName='Helvetica-Bold',
    )
    tw = doc.width
    empty = Paragraph('', val_st)
    meta_rows = [
        [
            Paragraph('SOLICITANTE', lab_st),
            Paragraph(xml_escape(sol), val_st),
            Paragraph('FUNÇÃO', lab_st),
            Paragraph(xml_escape(funcao), val_st),
        ],
        [Paragraph('LOCAL', lab_st), Paragraph(xml_escape(loc), val_st), empty, empty],
        [Paragraph('OBRA', lab_st), Paragraph(xml_escape(obr), val_st), empty, empty],
        [Paragraph('ALMOXARIFE', lab_st), Paragraph(xml_escape(alm), val_st), empty, empty],
    ]
    meta_tbl = Table(
        meta_rows,
        colWidths=[tw * 0.14, tw * 0.36, tw * 0.14, tw * 0.36],
    )
    meta_tbl.setStyle(
        TableStyle(
            [
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('SPAN', (1, 1), (3, 1)),
                ('SPAN', (1, 2), (3, 2)),
                ('SPAN', (1, 3), (3, 3)),
            ]
        )
    )
    story.append(meta_tbl)
    story.append(Spacer(1, 5 * mm))

    h_style = ParagraphStyle(
        'req_th',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
    )
    c_style = ParagraphStyle(
        'req_td',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
    )
    data = [
        [
            Paragraph('Item', h_style),
            Paragraph('Qtd', h_style),
            Paragraph('Un.', h_style),
        ]
    ]
    if itens:
        for ri in itens:
            desc = ri.item.descricao if ri.item_id and ri.item else '—'
            un = (
                ri.item.unidade_medida.abreviada
                if ri.item and ri.item.unidade_medida_id
                else '—'
            )
            data.append(
                [
                    Paragraph(xml_escape(desc), c_style),
                    Paragraph(xml_escape(fmt_quantidade_requisicao(ri.quantidade)), c_style),
                    Paragraph(xml_escape(str(un)), c_style),
                ]
            )
    else:
        data.append(
            [
                Paragraph('Sem itens.', c_style),
                Paragraph('', c_style),
                Paragraph('', c_style),
            ]
        )
    t_items = Table(data, colWidths=[tw * 0.62, tw * 0.25, tw * 0.13])
    t_items.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#e2e8f0')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t_items)
    story.append(Spacer(1, 10 * mm))

    assin_txt = (
        '_____________________________<br/><font size="8" color="#64748b">'
        'Assinatura do solicitante</font>'
    )
    assin_txt2 = (
        '_____________________________<br/><font size="8" color="#64748b">'
        'Assinatura do almoxarife</font>'
    )
    c_style_assin_dir = ParagraphStyle(
        'req_assin_dir',
        parent=c_style,
        alignment=TA_RIGHT,
    )
    gap_w = tw * 0.12
    col_assin = (tw - gap_w) / 2
    assin = Table(
        [
            [
                Paragraph(assin_txt, c_style),
                Paragraph('', c_style),
                Paragraph(assin_txt2, c_style_assin_dir),
            ]
        ],
        colWidths=[col_assin, gap_w, col_assin],
    )
    assin.setStyle(
        TableStyle(
            [
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (1, 0), (1, 0), 0),
                ('RIGHTPADDING', (1, 0), (1, 0), 0),
            ]
        )
    )
    story.append(assin)
    return story


def build_requisicao_pdf_bytes(empresa, requisicao, itens) -> bytes:
    buf = BytesIO()
    temp_paths: List[str] = []
    try:
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=12 * mm,
            bottomMargin=12 * mm,
        )
        styles = getSampleStyleSheet()
        story: list = []
        # Cada via fica junta; se ambas couberem na página, ficam na mesma; senão a 2ª desce inteira.
        story.append(
            KeepTogether(
                _story_via(
                    empresa=empresa,
                    requisicao=requisicao,
                    itens=itens,
                    via_label='Via do almoxarife',
                    doc=doc,
                    styles=styles,
                    temp_paths=temp_paths,
                )
            )
        )
        story.append(Spacer(1, 3 * mm))
        story.append(_LinhaCorteEntreVias(doc.width))
        story.append(Spacer(1, 3 * mm))
        story.append(
            KeepTogether(
                _story_via(
                    empresa=empresa,
                    requisicao=requisicao,
                    itens=itens,
                    via_label='Via do solicitante',
                    doc=doc,
                    styles=styles,
                    temp_paths=temp_paths,
                )
            )
        )
        doc.build(story)
        return buf.getvalue()
    finally:
        _unlink_temp_logo_paths(temp_paths)
