"""
Exportação PDF da tabela de Alterações de folha (mesmo padrão visual do Vale Transporte).
"""
from __future__ import annotations

import re
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape as xml_escape

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse
from empresas.models import Empresa
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from controles_rh.models import AlteracaoFolhaControle, AlteracaoFolhaLinha
from controles_rh.views.cesta_export import (
    _flowables_header_compact,
    _flowables_titulo_pdf_centro,
    _linha_extra_cabecalho_recibo,
    _mes_nome_pt,
    _nome_empresa_pdf,
    _unlink_temp_logo_paths,
)
from controles_rh.views.alteracao_folha import (
    _fmt_af_horas,
    _fmt_af_moeda,
    _get_competencia_empresa,
    _monta_linhas_tabela,
    _queryset_linhas,
    garantir_linhas_alteracao_folha,
)
from controles_rh.views.pdf_rodape import flowables_rodape_impressao

# Mesma largura útil do PDF VT (paisagem A4, margens 12 mm)
AF_PDF_TABLE_WIDTH_MM = 273

# Blocos (alinhado ao detalhe HTML): cadastro | adicionais | descontos
AF_COL_LAST_CADASTRO = 4
AF_COL_LAST_ADICIONAIS = 9
AF_COL_LAST_DESC = 13

# Cores próximas de templates/rh/alteracao_folha (af-th-ad / af-th-desc / fundos)
AF_COLOR_HEADER_CAD = colors.HexColor('#f8fafc')
AF_COLOR_HEADER_AD = colors.HexColor('#dbeafe')
AF_COLOR_HEADER_DESC = colors.HexColor('#fecdd3')
AF_COLOR_BODY_CAD = colors.HexColor('#fafbfc')
AF_COLOR_BODY_AD = colors.HexColor('#eef2ff')
AF_COLOR_BODY_DESC = colors.HexColor('#fff1f2')
AF_COLOR_LEGEND_ROW_CAD = colors.HexColor('#f1f5f9')
AF_COLOR_LEGEND_ROW_AD = colors.HexColor('#e8eeff')
AF_COLOR_LEGEND_ROW_DESC = colors.HexColor('#fce8ec')
AF_COLOR_TOTALS_ROW = colors.HexColor('#e0f2fe')


def _totais_formatados_por_coluna(competencia) -> dict[str, str]:
    """Soma por campo numérico, formatada como na tabela."""
    z = Decimal('0')
    agg = AlteracaoFolhaLinha.objects.filter(competencia=competencia).aggregate(
        th=Sum('hora_extra'),
        tf=Sum('horas_feriado'),
        ad=Sum('adicional'),
        pr=Sum('premio'),
        oa=Sum('outro_adicional'),
        ds=Sum('descontos'),
        od=Sum('outro_desconto'),
    )

    def nz(v):
        return v if v is not None else z

    th, tf = nz(agg['th']), nz(agg['tf'])
    ad, pr, oa = nz(agg['ad']), nz(agg['pr']), nz(agg['oa'])
    ds, od = nz(agg['ds']), nz(agg['od'])
    return {
        'he': _fmt_af_horas(th),
        'hf': _fmt_af_horas(tf),
        'ad': _fmt_af_moeda(ad),
        'pr': _fmt_af_moeda(pr),
        'oa': _fmt_af_moeda(oa),
        'ds': _fmt_af_moeda(ds),
        'od': _fmt_af_moeda(od),
    }


def _safe_filename_part(text: str) -> str:
    s = re.sub(r'[^\w\s\-]', '_', str(text), flags=re.UNICODE)
    s = re.sub(r'\s+', '_', s.strip())
    return (s[:60] or 'af').strip('_')


def _header_text_html_af(empresa, comp, _controle):
    """Cabeçalho PDF (bloco igual ao VT / cesta)."""
    nome = _nome_empresa_pdf(empresa)
    bits = [f'<b>{xml_escape(nome)}</b>']
    razao = (empresa.razao_social or '').strip()
    if razao and razao.upper() != (nome or '').upper():
        bits.append(f'<font size="8" color="#64748b">{xml_escape(razao)}</font>')
    bits.append(xml_escape(f'Alterações de folha · Competência {comp.referencia}'))
    extra = _linha_extra_cabecalho_recibo(empresa)
    if extra:
        bits.append(xml_escape(extra))
    email = (getattr(empresa, 'email', None) or '').strip()
    if email:
        bits.append(xml_escape(f'E-mail: {email}'))
    return '<br/>'.join(bits)


def _af_col_widths_mm() -> list[float]:
    """
    Colunas de faltas (11–12) estreitas; o espaço sobra para nome e valores.
    Índices: 0–4 cadastro, 5–9 adicionais, 10–13 descontos (10 desc $, 11–12 faltas, 13 out desc).
    """
    raw = [
        5.0,
        52.0,
        26.0,
        8.0,
        8.0,
        9.5,
        9.5,
        11.0,
        11.0,
        11.0,
        11.0,
        15.0,
        15.0,
        13.0,
    ]
    s = sum(raw)
    return [w * (AF_PDF_TABLE_WIDTH_MM / s) for w in raw]


@login_required
def exportar_alteracao_folha_pdf(request, competencia_pk):
    competencia = _get_competencia_empresa(request, competencia_pk)
    if not AlteracaoFolhaControle.objects.filter(competencia=competencia).exists():
        return HttpResponse(
            'Gere a alteração de folha na competência antes de exportar o PDF.',
            status=400,
            content_type='text/plain; charset=utf-8',
        )

    garantir_linhas_alteracao_folha(competencia)
    empresa = Empresa.objects.get(pk=competencia.empresa_id)
    controle = AlteracaoFolhaControle.objects.filter(competencia=competencia).first()
    qs = _queryset_linhas(competencia)
    linhas = _monta_linhas_tabela(competencia, qs)
    totais_cols = _totais_formatados_por_coluna(competencia)

    styles = getSampleStyleSheet()
    nome_style = ParagraphStyle(
        'af_nome',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9,
        spaceBefore=0,
        spaceAfter=0,
    )
    cell_style = ParagraphStyle(
        'af_cell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=9,
        spaceBefore=0,
        spaceAfter=0,
    )
    falta_style = ParagraphStyle(
        'af_falta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6,
        leading=8,
        spaceBefore=0,
        spaceAfter=0,
    )
    legend_style = ParagraphStyle(
        'af_legend',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6,
        leading=7.5,
        spaceBefore=0,
        spaceAfter=0,
        textColor=colors.HexColor('#475569'),
    )

    headers = [
        'Nº',
        'FUNCIONÁRIO',
        'FUNÇÃO',
        'VT',
        'SAL.\nFAM.',
        'H.EX.\n(h)',
        'H.FER.\n(h)',
        'ADIC.\n(R$)',
        'PRÊM.\n(R$)',
        'OUT.\nADIC.',
        'DESC.\n(R$)',
        'FALT.\nN.J.',
        'FALT.\nJ.',
        'OUT.\nDESC.',
    ]

    # Tabela principal: somente cabeçalho + dados (legendas ficam após a tabela).
    data_rows = [headers]
    for row in linhas:
        vt_txt = 'Sim' if row['passagem_sim'] else 'Não'
        nome_cell = Paragraph(xml_escape((row['funcionario'].nome or '').upper()), nome_style)
        func_cell = Paragraph(xml_escape(str(row['funcao'] or '—')), cell_style)
        data_rows.append(
            [
                str(row['seq']),
                nome_cell,
                func_cell,
                vt_txt,
                xml_escape(str(row['salario_familia_txt'])),
                xml_escape(row['hora_extra_fmt']),
                xml_escape(row['horas_feriado_fmt']),
                xml_escape(row['adicional_fmt']),
                xml_escape(row['premio_fmt']),
                xml_escape(row['outro_adicional_fmt']),
                xml_escape(row['descontos_fmt']),
                Paragraph(xml_escape(str(row['faltas_nj'])), falta_style),
                Paragraph(xml_escape(str(row['faltas_j'])), falta_style),
                xml_escape(row['outro_desconto_fmt']),
            ]
        )

    totals_row = [
        '',
        'TOTAIS',
        '',
        '',
        '',
        xml_escape(totais_cols['he']),
        xml_escape(totais_cols['hf']),
        xml_escape(totais_cols['ad']),
        xml_escape(totais_cols['pr']),
        xml_escape(totais_cols['oa']),
        xml_escape(totais_cols['ds']),
        '—',
        '—',
        xml_escape(totais_cols['od']),
    ]
    data_rows.append(totals_row)

    mes_titulo = f'{_mes_nome_pt(competencia.mes).upper()} {competencia.ano}'
    titulo_doc = f'ALTERAÇÕES DE FOLHA — {mes_titulo}'

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f'Alterações de folha {competencia.referencia}',
    )
    story = []
    temp_logo_paths = []
    story.extend(
        _flowables_header_compact(
            empresa,
            competencia,
            controle,
            styles,
            _header_text_html_af,
            temp_logo_paths,
        )
    )
    story.extend(_flowables_titulo_pdf_centro(titulo_doc, styles))

    cw = [w * mm for w in _af_col_widths_mm()]
    last_idx = len(data_rows) - 1
    i_first_data = 1
    i_last_data = last_idx - 1
    n_data = max(0, last_idx - 1)

    table = Table(data_rows, colWidths=cw, repeatRows=1)
    pdf_style = [
        # Linha 0 — títulos abreviados (blocos)
        ('BACKGROUND', (0, 0), (AF_COL_LAST_CADASTRO, 0), AF_COLOR_HEADER_CAD),
        ('BACKGROUND', (5, 0), (AF_COL_LAST_ADICIONAIS, 0), AF_COLOR_HEADER_AD),
        ('BACKGROUND', (10, 0), (AF_COL_LAST_DESC, 0), AF_COLOR_HEADER_DESC),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (3, 0), (4, 0), 'CENTER'),
        ('ALIGN', (5, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (5, 0), (10, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cbd5e1')),
        # Linha de totais (última)
        ('BACKGROUND', (0, last_idx), (-1, last_idx), AF_COLOR_TOTALS_ROW),
        ('FONTNAME', (0, last_idx), (-1, last_idx), 'Helvetica-Bold'),
        ('FONTSIZE', (0, last_idx), (-1, last_idx), 7),
        ('ALIGN', (0, last_idx), (0, last_idx), 'CENTER'),
        ('ALIGN', (1, last_idx), (1, last_idx), 'LEFT'),
        ('ALIGN', (5, last_idx), (10, last_idx), 'RIGHT'),
        ('ALIGN', (11, last_idx), (12, last_idx), 'CENTER'),
        ('ALIGN', (13, last_idx), (13, last_idx), 'RIGHT'),
        ('VALIGN', (0, last_idx), (-1, last_idx), 'MIDDLE'),
    ]
    # Dados (entre legenda e totais)
    if n_data >= 1:
        pdf_style.extend(
            [
                ('ALIGN', (3, i_first_data), (4, i_last_data), 'CENTER'),
                ('ALIGN', (0, i_first_data), (0, i_last_data), 'CENTER'),
                ('ALIGN', (5, i_first_data), (10, i_last_data), 'RIGHT'),
                ('ALIGN', (11, i_first_data), (12, i_last_data), 'LEFT'),
                ('ALIGN', (13, i_first_data), (13, i_last_data), 'RIGHT'),
                (
                    'BACKGROUND',
                    (0, i_first_data),
                    (AF_COL_LAST_CADASTRO, i_last_data),
                    AF_COLOR_BODY_CAD,
                ),
                (
                    'BACKGROUND',
                    (5, i_first_data),
                    (AF_COL_LAST_ADICIONAIS, i_last_data),
                    AF_COLOR_BODY_AD,
                ),
                (
                    'BACKGROUND',
                    (10, i_first_data),
                    (AF_COL_LAST_DESC, i_last_data),
                    AF_COLOR_BODY_DESC,
                ),
            ]
        )
    if last_idx >= 3:
        pdf_style.extend(
            [
                ('FONTSIZE', (0, 1), (-1, last_idx - 1), 7),
                ('VALIGN', (0, 1), (-1, last_idx - 1), 'TOP'),
            ]
        )

    table.setStyle(TableStyle(pdf_style))
    story.append(table)

    # Legendas (após a tabela): somente siglas abreviadas do cabeçalho.
    legend_items = [
        ('VT', 'Vale transporte'),
        ('SAL. FAM.', 'Salário família'),
        ('H.EX. (h)', 'Horas extras (horas)'),
        ('H.FER. (h)', 'Horas em feriado (horas)'),
        ('ADIC. (R$)', 'Adicionais (R$)'),
        ('PRÊM. (R$)', 'Prêmio (R$)'),
        ('OUT. ADIC.', 'Outro adicional'),
        ('DESC. (R$)', 'Descontos (R$)'),
        ('FALT. N.J.', 'Faltas não justificadas (dias)'),
        ('FALT. J.', 'Faltas justificadas (dias)'),
        ('OUT. DESC.', 'Outro desconto'),
    ]
    legend_cells = []
    for sigla, desc in legend_items:
        legend_cells.append(
            Paragraph(
                f'<font name="Helvetica-Bold">{xml_escape(sigla)}</font> — {xml_escape(desc)}',
                legend_style,
            )
        )

    # Grid para caber em paisagem A4: 3 colunas (ajusta bem no espaço).
    legend_cols = 3
    legend_rows = []
    for i in range(0, len(legend_cells), legend_cols):
        row = legend_cells[i : i + legend_cols]
        if len(row) < legend_cols:
            row.extend([''] * (legend_cols - len(row)))
        legend_rows.append(row)

    story.append(Spacer(1, 3 * mm))
    legend_table = Table(
        legend_rows,
        colWidths=[(AF_PDF_TABLE_WIDTH_MM / legend_cols) * mm] * legend_cols,
    )
    legend_table.setStyle(
        TableStyle(
            [
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ]
        )
    )
    story.append(legend_table)

    story.extend(flowables_rodape_impressao(request, styles, space_before_mm=3))

    doc.build(story)
    _unlink_temp_logo_paths(temp_logo_paths)
    buf.seek(0)

    ref = f'{competencia.mes:02d}_{competencia.ano}'
    emp_part = _safe_filename_part(_nome_empresa_pdf(empresa))
    filename = f'Alteracao_folha_{emp_part}_{ref}.pdf'

    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    # aspas para nomes com espaço no download
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
