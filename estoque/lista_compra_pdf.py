"""PDF da lista de compra (almoxarifado) — ReportLab, cabeçalho alinhado à requisição."""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from typing import List, Optional
from xml.sax.saxutils import escape as xml_escape

from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from controles_rh.views.cesta_export import _unlink_temp_logo_paths

from .models import ListaCompraEstoque
from .requisicao_export import _tabela_cabecalho_empresa
from .requisicao_qty_fmt import fmt_quantidade_requisicao


def _fmt_real_br(val: Optional[Decimal]) -> str:
    if val is None:
        return ''
    x = Decimal(str(val)).quantize(Decimal('0.01'))
    neg = x < 0
    x = abs(x)
    s = f'{x:.2f}'
    head, tail = s[:-3], s[-2:]
    rev = head[::-1]
    chunks = [rev[i : i + 3] for i in range(0, len(rev), 3)]
    head_fmt = '.'.join(chunks)[::-1]
    out = f'{head_fmt},{tail}'
    return f'-{out}' if neg else out


def _cell_marca(item) -> str:
    if not item:
        return '—'
    m = (getattr(item, 'marca', None) or '').strip()
    return m if m else '—'


def _cell_preco(item) -> str:
    if not item or getattr(item, 'preco', None) is None:
        return '—'
    return f'R$ {_fmt_real_br(item.preco)}'


def _cell_fornecedor(item) -> str:
    if not item or not getattr(item, 'fornecedor_id', None):
        return '—'
    f = getattr(item, 'fornecedor', None)
    if not f:
        return '—'
    n = (f.nome or '').strip()
    return n if n else '—'


def build_lista_compra_pdf_bytes(empresa, lista: ListaCompraEstoque, itens) -> bytes:
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
        tw = doc.width
        left_w = tw * 0.62
        right_w = tw - left_w

        story: list = []
        left_tbl = _tabela_cabecalho_empresa(
            empresa,
            styles,
            temp_paths,
            left_w,
        )

        if lista.criado_em:
            data_txt = timezone.localtime(lista.criado_em).strftime('%d/%m/%Y %H:%M')
        else:
            data_txt = '—'

        sub_r = ParagraphStyle(
            'lc_via_lbl_r',
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
            'lc_tit_r',
            parent=styles['Normal'],
            fontSize=13,
            leading=16,
            fontName='Helvetica-Bold',
            spaceAfter=1 * mm,
            alignment=TA_RIGHT,
        )
        meta_r = ParagraphStyle(
            'lc_meta_r',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#475569'),
            alignment=TA_RIGHT,
        )

        nome_txt = (lista.nome or '').strip()
        titulo_linha = (
            nome_txt if nome_txt else f'Lista de compra nº {lista.pk}'
        )
        right_rows = [
            [Paragraph('LISTA DE COMPRAS', sub_r)],
            [Paragraph(xml_escape(titulo_linha), tit_r)],
            [
                Paragraph(
                    xml_escape(
                        f'Data do pedido {lista.data_pedido:%d/%m/%Y} · '
                        f'{lista.get_status_display()} · Registrada em {data_txt}'
                    ),
                    meta_r,
                )
            ],
        ]
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

        alm = '—'
        if lista.criado_por_id:
            u = lista.criado_por
            alm = (u.nome_completo or u.username or '—') if u else '—'

        lab_st = ParagraphStyle(
            'lc_lab',
            parent=styles['Normal'],
            fontSize=7,
            leading=9,
            textColor=colors.HexColor('#64748b'),
        )
        val_st = ParagraphStyle(
            'lc_val',
            parent=styles['Normal'],
            fontSize=9,
            leading=11,
            fontName='Helvetica-Bold',
        )
        empty = Paragraph('', val_st)
        obs_geral = (lista.observacoes or '').strip() or '—'
        meta_rows = [
            [
                Paragraph('SOLICITADO POR', lab_st),
                Paragraph(xml_escape(alm), val_st),
                empty,
                empty,
            ],
            [
                Paragraph('OBS. GERAIS', lab_st),
                Paragraph(xml_escape(obs_geral), val_st),
                empty,
                empty,
            ],
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
                    ('SPAN', (1, 0), (3, 0)),
                    ('SPAN', (1, 1), (3, 1)),
                ]
            )
        )
        story.append(meta_tbl)
        story.append(Spacer(1, 5 * mm))

        h_style = ParagraphStyle(
            'lc_th',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=11,
        )
        c_style = ParagraphStyle(
            'lc_td',
            parent=styles['Normal'],
            fontSize=9,
            leading=11,
        )
        data = [
            [
                Paragraph('Item', h_style),
                Paragraph('Marca', h_style),
                Paragraph('Preço', h_style),
                Paragraph('Fornecedor', h_style),
                Paragraph('Qtd a comprar', h_style),
                Paragraph('Un.', h_style),
                Paragraph('Obs.', h_style),
            ]
        ]
        if itens:
            for li in itens:
                it = li.item if li.item_id else None
                desc = it.descricao if it else '—'
                un = (
                    it.unidade_medida.abreviada
                    if it and it.unidade_medida_id
                    else '—'
                )
                obs = (li.observacoes or '').strip() or '—'
                data.append(
                    [
                        Paragraph(xml_escape(desc), c_style),
                        Paragraph(xml_escape(_cell_marca(it)), c_style),
                        Paragraph(xml_escape(_cell_preco(it)), c_style),
                        Paragraph(xml_escape(_cell_fornecedor(it)), c_style),
                        Paragraph(
                            xml_escape(fmt_quantidade_requisicao(li.quantidade_comprar)),
                            c_style,
                        ),
                        Paragraph(xml_escape(str(un)), c_style),
                        Paragraph(xml_escape(obs), c_style),
                    ]
                )
        else:
            data.append(
                [
                    Paragraph('Sem itens.', c_style),
                    Paragraph('', c_style),
                    Paragraph('', c_style),
                    Paragraph('', c_style),
                    Paragraph('', c_style),
                    Paragraph('', c_style),
                    Paragraph('', c_style),
                ]
            )
        col_item = tw * 0.26
        col_marca = tw * 0.10
        col_preco = tw * 0.10
        col_forn = tw * 0.14
        col_qtd = tw * 0.12
        col_un = tw * 0.08
        col_obs = tw * 0.20
        t_items = Table(
            data,
            colWidths=[
                col_item,
                col_marca,
                col_preco,
                col_forn,
                col_qtd,
                col_un,
                col_obs,
            ],
        )
        t_items.setStyle(
            TableStyle(
                [
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#e2e8f0')),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                    ('ALIGN', (4, 0), (5, -1), 'CENTER'),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(t_items)

        doc.build(story)
        return buf.getvalue()
    finally:
        _unlink_temp_logo_paths(temp_paths)
