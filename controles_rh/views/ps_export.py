"""
Exportação PDF da planilha de Pagamento de salário.
Segue o padrão visual do PDF de Alterações de folha.
"""
from __future__ import annotations

import re
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape as xml_escape

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from controles_rh.views.cesta_export import (
    _flowables_header_compact,
    _flowables_titulo_pdf_centro,
    _linha_extra_cabecalho_recibo,
    _mes_nome_pt,
    _nome_empresa_pdf,
    _unlink_temp_logo_paths,
)
from controles_rh.views.pagamento_salario import (
    _fmt_af_moeda,
    _get_controle_pagamento_empresa,
    _monta_linhas_tabela,
    _ordenacao_linhas,
    _queryset_linhas,
    _totais_pagamento_salario,
)
from controles_rh.views.pdf_avatar import AvatarFuncionario
from controles_rh.views.pdf_rodape import flowables_rodape_impressao


PS_PDF_TABLE_WIDTH_MM = 273
PS_COLOR_HEADER_BASE = colors.HexColor('#f8fafc')
PS_COLOR_HEADER_VALOR = colors.HexColor('#bbf7d0')
PS_COLOR_BODY_BASE = colors.HexColor('#fafbfc')
PS_COLOR_BODY_VALOR = colors.HexColor('#dcfce7')
PS_COLOR_TOTALS_ROW = colors.HexColor('#e0f2fe')


def _safe_filename_part(text: str) -> str:
    s = re.sub(r'[^\w\s\-]', '_', str(text), flags=re.UNICODE)
    s = re.sub(r'\s+', '_', s.strip())
    return (s[:60] or 'pagamento_salario').strip('_')


def _header_text_html_ps(empresa, comp, controle):
    nome = _nome_empresa_pdf(empresa)
    bits = [f'<b>{xml_escape(nome)}</b>']
    razao = (empresa.razao_social or '').strip()
    if razao and razao.upper() != (nome or '').upper():
        bits.append(f'<font size="8" color="#64748b">{xml_escape(razao)}</font>')
    bits.append(xml_escape(f'{controle.nome_exibicao} - Competência {comp.referencia}'))
    extra = _linha_extra_cabecalho_recibo(empresa)
    if extra:
        bits.append(xml_escape(extra))
    email = (getattr(empresa, 'email', None) or '').strip()
    if email:
        bits.append(xml_escape(f'E-mail: {email}'))
    return '<br/>'.join(bits)


def _ps_col_widths_mm() -> list[float]:
    raw = [7.0, 74.0, 27.0, 24.0, 64.0, 77.0]
    total = sum(raw)
    return [w * (PS_PDF_TABLE_WIDTH_MM / total) for w in raw]


def _pdf_text(value) -> str:
    return str(value if value is not None else '-').replace('—', '-')


def _totais_resumo_pdf(linhas: list[dict], total_pagar_fmt: str) -> list[list[str]]:
    por_lotacao: dict[str, Decimal] = {}
    por_banco: dict[str, Decimal] = {}
    for row in linhas:
        valor = row['linha'].valor or Decimal('0.00')
        lotacao = _pdf_text(row.get('lotacao')).strip()
        if lotacao in {'', '-'}:
            lotacao = 'Sem lotação'
        banco = _pdf_text(row.get('banco_empresa')).strip()
        if banco in {'', '-'}:
            banco = 'Sem banco empresa'
        por_lotacao[lotacao] = por_lotacao.get(lotacao, Decimal('0.00')) + valor
        por_banco[banco] = por_banco.get(banco, Decimal('0.00')) + valor

    rows = [['Total R$:', f'R$ {total_pagar_fmt}']]
    for lotacao, total in sorted(por_lotacao.items(), key=lambda item: item[0].lower()):
        rows.append([f'Total {lotacao}:', f'R$ {_fmt_af_moeda(total)}'])
    for banco, total in sorted(por_banco.items(), key=lambda item: item[0].lower()):
        rows.append([f'Total {banco}:', f'R$ {_fmt_af_moeda(total)}'])
    rows.append(['Total Funcionários:', str(len(linhas))])
    return rows


@login_required
def exportar_pagamento_salario_pdf(request, controle_pk):
    controle = _get_controle_pagamento_empresa(request, controle_pk)
    competencia = controle.competencia

    ordenacao = _ordenacao_linhas(request.GET.get('ordenacao'))
    qs = _queryset_linhas(controle, ordenacao=ordenacao)
    linhas = _monta_linhas_tabela(competencia, controle, qs)
    totais = _totais_pagamento_salario(controle)

    empresa = competencia.empresa
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle(
        'ps_cell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        spaceBefore=0,
        spaceAfter=0,
    )
    small_style = ParagraphStyle(
        'ps_small',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.4,
        leading=9.2,
        spaceBefore=0,
        spaceAfter=0,
    )
    valor_style = ParagraphStyle(
        'ps_valor',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=11,
        alignment=1,
        textColor=colors.HexColor('#166534'),
        spaceBefore=0,
        spaceAfter=0,
    )
    resumo_label_style = ParagraphStyle(
        'ps_resumo_label',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        alignment=2,
        textColor=colors.HexColor('#334155'),
        spaceBefore=0,
        spaceAfter=0,
    )
    resumo_value_style = ParagraphStyle(
        'ps_resumo_value',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=10,
        alignment=2,
        textColor=colors.HexColor('#166534'),
        spaceBefore=0,
        spaceAfter=0,
    )

    headers = [
        'Nº',
        'FUNCIONÁRIO',
        'CPF',
        'VALOR',
        'DADOS DO PIX',
        'BANCO EMPRESA',
    ]
    data_rows = [headers]
    for row in linhas:
        funcionario = row['funcionario']
        nome = xml_escape((funcionario.nome or '').upper())
        cargo = xml_escape(_pdf_text(row['funcao']))
        lotacao = xml_escape(_pdf_text(row['lotacao']))
        admissao = xml_escape(_pdf_text(row['data_admissao_fmt']))
        tempo_admissao = xml_escape(_pdf_text(row['tempo_admissao_fmt']))
        funcionario_text = Paragraph(
            (
                f'<b>{nome}</b><br/>'
                f'<font size="6">{cargo}<br/>'
                f'Lotação: {lotacao}<br/>Admissão: {admissao} ({tempo_admissao})</font>'
            ),
            cell_style,
        )
        funcionario_cell = Table(
            [[AvatarFuncionario(funcionario, 8 * mm), funcionario_text]],
            colWidths=[9 * mm, 62 * mm],
        )
        funcionario_cell.setStyle(
            TableStyle(
                [
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ]
            )
        )
        dados_pix = row['dados_pix']
        pix_cell = Paragraph(
            (
                f'Tipo: {xml_escape(_pdf_text(dados_pix["tipo"]))}<br/>'
                f'{xml_escape(_pdf_text(dados_pix["chave"]))}<br/>'
                f'Banco: {xml_escape(_pdf_text(dados_pix["banco"]))}'
            ),
            small_style,
        )
        data_rows.append(
            [
                str(row['seq']),
                funcionario_cell,
                xml_escape(_pdf_text(row['cpf'])),
                Paragraph(xml_escape(f'R$ {row["valor_fmt"]}'), valor_style),
                pix_cell,
                Paragraph(xml_escape(_pdf_text(row['banco_empresa'])), small_style),
            ]
        )

    data_rows.append(
        ['', 'TOTAIS', '', Paragraph(f'R$ {totais["total_pagar_fmt"]}', valor_style), '', '']
    )

    mes_titulo = f'{_mes_nome_pt(competencia.mes).upper()} {competencia.ano}'
    titulo_doc = f'{controle.nome_exibicao.upper()} - {mes_titulo}'

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f'{controle.nome_exibicao} {competencia.referencia}',
    )
    story = []
    temp_logo_paths = []
    story.extend(
        _flowables_header_compact(
            empresa,
            competencia,
            controle,
            styles,
            _header_text_html_ps,
            temp_logo_paths,
        )
    )
    story.extend(_flowables_titulo_pdf_centro(titulo_doc, styles))

    last_idx = len(data_rows) - 1
    i_first_data = 1
    i_last_data = last_idx - 1

    table = Table(data_rows, colWidths=[w * mm for w in _ps_col_widths_mm()], repeatRows=1)
    pdf_style = [
        ('BACKGROUND', (0, 0), (-1, 0), PS_COLOR_HEADER_BASE),
        ('BACKGROUND', (3, 0), (3, 0), PS_COLOR_HEADER_VALOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0, last_idx), (-1, last_idx), PS_COLOR_TOTALS_ROW),
        ('BACKGROUND', (3, last_idx), (3, last_idx), PS_COLOR_BODY_VALOR),
        ('FONTNAME', (0, last_idx), (-1, last_idx), 'Helvetica-Bold'),
        ('TEXTCOLOR', (3, last_idx), (3, last_idx), colors.HexColor('#166534')),
        ('FONTSIZE', (0, last_idx), (-1, last_idx), 8),
        ('ALIGN', (0, last_idx), (0, last_idx), 'CENTER'),
        ('ALIGN', (1, last_idx), (1, last_idx), 'LEFT'),
        ('ALIGN', (3, last_idx), (3, last_idx), 'CENTER'),
        ('VALIGN', (0, last_idx), (-1, last_idx), 'MIDDLE'),
    ]
    if i_last_data >= i_first_data:
        pdf_style.extend(
            [
                ('BACKGROUND', (0, i_first_data), (-1, i_last_data), PS_COLOR_BODY_BASE),
                ('BACKGROUND', (3, i_first_data), (3, i_last_data), PS_COLOR_BODY_VALOR),
                ('FONTNAME', (3, i_first_data), (3, i_last_data), 'Helvetica-Bold'),
                ('TEXTCOLOR', (3, i_first_data), (3, i_last_data), colors.HexColor('#166534')),
                ('ALIGN', (0, i_first_data), (0, i_last_data), 'CENTER'),
                ('ALIGN', (2, i_first_data), (2, i_last_data), 'CENTER'),
                ('ALIGN', (3, i_first_data), (3, i_last_data), 'CENTER'),
                ('ALIGN', (4, i_first_data), (5, i_last_data), 'LEFT'),
                ('VALIGN', (0, i_first_data), (-1, i_last_data), 'TOP'),
                ('VALIGN', (3, i_first_data), (3, i_last_data), 'MIDDLE'),
                ('FONTSIZE', (0, i_first_data), (-1, i_last_data), 8),
            ]
        )

    table.setStyle(TableStyle(pdf_style))
    story.append(table)

    resumo_rows_raw = _totais_resumo_pdf(linhas, totais['total_pagar_fmt'])
    resumo_rows = [
        [
            Paragraph(xml_escape(label), resumo_label_style),
            Paragraph(xml_escape(value), resumo_value_style),
        ]
        for label, value in resumo_rows_raw
    ]
    resumo_table = Table(resumo_rows, colWidths=[58 * mm, 34 * mm], hAlign='RIGHT')
    resumo_table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
                ('BACKGROUND', (0, 0), (-1, 0), PS_COLOR_BODY_VALOR),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cbd5e1')),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]
        )
    )
    story.append(Spacer(1, 3 * mm))
    story.append(resumo_table)
    story.append(Spacer(1, 3 * mm))
    story.extend(flowables_rodape_impressao(request, styles, space_before_mm=3))

    doc.build(story)
    _unlink_temp_logo_paths(temp_logo_paths)
    buf.seek(0)

    ref = f'{competencia.mes:02d}_{competencia.ano}'
    emp_part = _safe_filename_part(_nome_empresa_pdf(empresa))
    nome_part = _safe_filename_part(controle.nome_exibicao)
    filename = f'{nome_part}_{emp_part}_{ref}.pdf'

    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
