import re
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape as xml_escape

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from controles_rh.views.vale_transporte import _get_tabela_vt_empresa, _total_valor_pago_tabela


def _safe_filename_part(text):
    s = re.sub(r'[^\w\s\-]', '_', str(text), flags=re.UNICODE)
    s = re.sub(r'\s+', '_', s.strip())
    return (s[:60] or 'vt').strip('_')


def _itens_export(tabela):
    return tabela.itens.select_related('funcionario').order_by('ordem', 'nome', 'id')


def _resumo_tabela_export(tabela):
    """
    Mesmos totais e metadados do cabeçalho da tela de detalhe (controle VT).
    """
    comp = tabela.competencia
    total_itens = tabela.itens.count()
    total_valor_pago = _total_valor_pago_tabela(tabela)
    total_a_pagar = tabela.total_valor
    saldo_a_pagar = total_a_pagar - total_valor_pago
    if saldo_a_pagar < 0:
        saldo_a_pagar = Decimal('0.00')
    return {
        'competencia': comp,
        'total_itens': total_itens,
        'total_a_pagar': total_a_pagar,
        'total_valor_pago': total_valor_pago,
        'saldo_a_pagar': saldo_a_pagar,
        'status_vt_label': tabela.vt_status_efetivo_label,
    }


def _row_data_pagamento(item):
    if item.data_pagamento:
        return item.data_pagamento.strftime('%d/%m/%Y')
    return '—'


def _fmt_br_decimal(val):
    """Exibe Decimal/float como string pt-BR para PDF."""
    v = float(val or 0)
    return f'{v:.2f}'.replace('.', ',')


@login_required
def exportar_tabela_vt_xlsx(request, pk):
    tabela = _get_tabela_vt_empresa(request, pk)
    comp = tabela.competencia
    resumo = _resumo_tabela_export(tabela)

    headers = [
        '#',
        'Nome',
        'Função',
        'Endereço',
        'Valor a pagar',
        'Valor pago',
        'Saldo',
        'Data pagamento',
        'Pix',
        'Tipo Pix',
        'Banco',
    ]
    ncols = len(headers)

    wb = Workbook()
    ws = wb.active
    ws.title = 'VT'

    row = 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
    c = ws.cell(row=row, column=1, value=f'{tabela.nome} — Competência {comp.referencia} — {comp.empresa}')
    c.font = Font(bold=True, size=12)
    c.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    row += 1

    desc_txt = (tabela.descricao or '').strip() or '—'
    left_rows = [
        ('Competência', comp.referencia),
        ('Empresa', str(comp.empresa)),
        ('Descrição', desc_txt),
    ]
    right_rows = [
        ('Total de itens', resumo['total_itens']),
        ('Total a pagar (R$)', float(resumo['total_a_pagar'])),
        ('Total pago (R$)', float(resumo['total_valor_pago'])),
        ('Saldo à pagar (R$)', float(resumo['saldo_a_pagar'])),
        ('Status pagamento (VT)', resumo['status_vt_label']),
    ]
    block_start = row
    max_lines = max(len(left_rows), len(right_rows))
    for i in range(max_lines):
        r = block_start + i
        if i < len(left_rows):
            la = ws.cell(row=r, column=1, value=left_rows[i][0])
            la.font = Font(bold=True)
            la.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
            lv = ws.cell(row=r, column=2, value=left_rows[i][1])
            lv.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
        if i < len(right_rows):
            ra = ws.cell(row=r, column=4, value=right_rows[i][0])
            ra.font = Font(bold=True)
            ra.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
            rv = ws.cell(row=r, column=5, value=right_rows[i][1])
            rv.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
    row = block_start + max_lines + 1

    for col, h in enumerate(headers, 1):
        hc = ws.cell(row=row, column=col, value=h)
        hc.font = Font(bold=True)
        hc.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    row += 1

    for n, item in enumerate(_itens_export(tabela), start=1):
        if not item.ativo or not item.valor_pagar or item.valor_pagar <= 0:
            saldo_val = '—'
        else:
            saldo_val = float(item.saldo)
        valores = [
            n,
            item.nome_exibicao,
            item.funcao or '',
            item.endereco or '',
            float(item.valor_pagar or 0),
            float(item.valor_pago or 0),
            saldo_val,
            _row_data_pagamento(item),
            item.pix or '',
            item.get_tipo_pix_display() or '',
            item.banco or '',
        ]
        for col, val in enumerate(valores, 1):
            ws.cell(row=row, column=col, value=val)
        row += 1

    ws.cell(row=row, column=1, value='TOTAIS').font = Font(bold=True)
    ws.cell(row=row, column=5, value=float(resumo['total_a_pagar'])).font = Font(bold=True)
    ws.cell(row=row, column=6, value=float(resumo['total_valor_pago'])).font = Font(bold=True)
    ws.cell(row=row, column=7, value=float(resumo['saldo_a_pagar'])).font = Font(bold=True)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    name = _safe_filename_part(tabela.nome)
    ref = f'{comp.mes:02d}_{comp.ano}'
    filename = f'VT_{name}_{ref}.xlsx'

    response = HttpResponse(
        buf.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def exportar_tabela_vt_pdf(request, pk):
    tabela = _get_tabela_vt_empresa(request, pk)
    comp = tabela.competencia
    resumo = _resumo_tabela_export(tabela)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        't',
        parent=styles['Heading2'],
        fontSize=11,
        spaceAfter=6,
    )
    # Tabela em duas linhas por item: (1) #, nome, valores, PIX  (2) demais campos mesclados
    headers = [
        '#',
        'Nome',
        'Vlr pagar',
        'Vlr pago',
        'Saldo',
        'Pix',
    ]

    desc_txt = (tabela.descricao or '').strip() or '—'
    if len(desc_txt) > 220:
        desc_txt = desc_txt[:217] + '…'

    # Esquerda: identificação | Direita: totais e status (melhor uso da folha)
    meta_rows = [
        [
            'Competência',
            comp.referencia,
            'Total de itens',
            str(resumo['total_itens']),
        ],
        [
            'Empresa',
            xml_escape(str(comp.empresa)),
            'Total a pagar (R$)',
            _fmt_br_decimal(resumo['total_a_pagar']),
        ],
        [
            'Descrição',
            xml_escape(desc_txt),
            'Total pago (R$)',
            _fmt_br_decimal(resumo['total_valor_pago']),
        ],
        [
            '',
            '',
            'Saldo à pagar (R$)',
            _fmt_br_decimal(resumo['saldo_a_pagar']),
        ],
        [
            '',
            '',
            'Status pagamento (VT)',
            xml_escape(str(resumo['status_vt_label'])),
        ],
    ]

    nome_para_style = ParagraphStyle(
        'vt_nom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=8,
        spaceBefore=0,
        spaceAfter=0,
    )
    pix_para_style = ParagraphStyle(
        'pixcell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=7,
        spaceBefore=0,
        spaceAfter=0,
    )
    detalhe_para_style = ParagraphStyle(
        'vt_det',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6,
        leading=7,
        spaceBefore=0,
        spaceAfter=0,
        textColor=colors.HexColor('#475569'),
    )

    data_rows = [headers]
    table_spans = []

    for n, item in enumerate(_itens_export(tabela), start=1):
        if not item.ativo or not item.valor_pagar or item.valor_pagar <= 0:
            saldo_s = '—'
        else:
            saldo_s = f'{item.saldo:.2f}'.replace('.', ',')
        pix_full = item.pix or '—'
        pix_cell = Paragraph(xml_escape(pix_full), pix_para_style)
        nome_cell = Paragraph(xml_escape(item.nome_exibicao or '—'), nome_para_style)

        main_row = [
            str(n),
            nome_cell,
            f'{item.valor_pagar or 0:.2f}'.replace('.', ','),
            f'{item.valor_pago or 0:.2f}'.replace('.', ','),
            saldo_s,
            pix_cell,
        ]
        data_rows.append(main_row)

        det_txt = (
            f'<b>Função:</b> {xml_escape(item.funcao or "—")} &nbsp;|&nbsp; '
            f'<b>Endereço:</b> {xml_escape(item.endereco or "—")}<br/>'
            f'<b>Dt.pag.:</b> {xml_escape(_row_data_pagamento(item))} &nbsp;|&nbsp; '
            f'<b>Tipo:</b> {xml_escape(item.get_tipo_pix_display() or "—")} &nbsp;|&nbsp; '
            f'<b>Banco:</b> {xml_escape(item.banco or "—")}'
        )
        det_cell = Paragraph(det_txt, detalhe_para_style)
        detail_row_idx = len(data_rows)
        data_rows.append(['', det_cell, '', '', '', ''])
        table_spans.append(('SPAN', (1, detail_row_idx), (5, detail_row_idx)))

    data_rows.append(
        [
            'TOTAIS',
            '',
            _fmt_br_decimal(resumo['total_a_pagar']),
            _fmt_br_decimal(resumo['total_valor_pago']),
            _fmt_br_decimal(resumo['saldo_a_pagar']),
            '',
        ]
    )

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f'VT {tabela.nome}',
    )
    story = [
        Paragraph(
            f'<b>{xml_escape(tabela.nome)}</b> — Competência {comp.referencia} — '
            f'{xml_escape(str(comp.empresa))}',
            title_style,
        ),
        Spacer(1, 2 * mm),
    ]

    meta_tbl = Table(
        meta_rows,
        colWidths=[34 * mm, 92 * mm, 44 * mm, 52 * mm],
    )
    meta_tbl.setStyle(
        TableStyle(
            [
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.2, colors.HexColor('#cbd5e1')),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ]
        )
    )
    story.append(meta_tbl)
    story.append(Spacer(1, 5 * mm))

    last_idx = len(data_rows) - 1
    # 6 colunas, soma 273mm — nome e PIX com Paragraph (quebra de linha)
    _cw = (8, 52, 24, 24, 22, 143)
    table = Table(data_rows, colWidths=[w * mm for w in _cw], repeatRows=1)
    pdf_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dbeafe')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 1), (4, last_idx - 1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('VALIGN', (0, 1), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0, last_idx), (-1, last_idx), colors.HexColor('#e0f2fe')),
        ('FONTNAME', (0, last_idx), (-1, last_idx), 'Helvetica-Bold'),
        ('ALIGN', (2, last_idx), (4, last_idx), 'RIGHT'),
    ]
    for span_cmd in table_spans:
        pdf_style.append(span_cmd)
    if last_idx > 1:
        pdf_style.append(
            (
                'ROWBACKGROUNDS',
                (0, 1),
                (-1, last_idx - 1),
                [
                    colors.white,
                    colors.white,
                    colors.HexColor('#f8fafc'),
                    colors.HexColor('#f8fafc'),
                ],
            )
        )
    table.setStyle(TableStyle(pdf_style))
    story.append(table)

    doc.build(story)
    buf.seek(0)

    name = _safe_filename_part(tabela.nome)
    ref = f'{comp.mes:02d}_{comp.ano}'
    filename = f'VT_{name}_{ref}.pdf'

    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
