import re
from io import BytesIO
from xml.sax.saxutils import escape as xml_escape

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from controles_rh.views.cesta_basica import _get_lista_cesta_empresa


def _safe_filename_part(text):
    s = re.sub(r'[^\w\s\-]', '_', str(text), flags=re.UNICODE)
    s = re.sub(r'\s+', '_', s.strip())
    return (s[:60] or 'cesta').strip('_')


def _mes_nome_pt(mes):
    nomes = (
        'Janeiro',
        'Fevereiro',
        'Março',
        'Abril',
        'Maio',
        'Junho',
        'Julho',
        'Agosto',
        'Setembro',
        'Outubro',
        'Novembro',
        'Dezembro',
    )
    if 1 <= mes <= 12:
        return nomes[mes - 1]
    return str(mes)


def _itens_export(lista):
    return lista.itens.select_related('funcionario').order_by('ordem', 'nome', 'id')


def _nome_empresa_pdf(empresa):
    return (getattr(empresa, 'nome_fantasia', None) or '').strip() or getattr(
        empresa, 'razao_social', ''
    ) or 'Empresa'


def _texto_declaracao_padrao(lista):
    if (lista.texto_declaracao or '').strip():
        return lista.texto_declaracao.strip()
    nome = _nome_empresa_pdf(lista.competencia.empresa)
    return (
        f'DECLARO QUE RECEBI DA {nome.upper()}, NA DATA ABAIXO, A CESTA BÁSICA DE ALIMENTOS.'
    )


def _data_rodape_pt(lista):
    if lista.data_emissao_recibo:
        d = lista.data_emissao_recibo
        return f'{d.day:02d} DE {_mes_nome_pt(d.month).upper()} DE {d.year}'
    return '___ DE ______________ DE ______'


def _cell_styles_base(styles):
    cell_txt = ParagraphStyle(
        'cb_cell_txt',
        parent=styles['Normal'],
        fontSize=7,
        leading=8.5,
        spaceBefore=0,
        spaceAfter=0,
    )
    cell_num = ParagraphStyle(
        'cb_cell_num',
        parent=cell_txt,
        alignment=1,
        fontName='Helvetica',
    )
    return cell_txt, cell_num


def _table_style_base(last_idx):
    pdf_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dbeafe')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cbd5e1')),
    ]
    if last_idx > 0:
        pdf_style.append(
            (
                'ROWBACKGROUNDS',
                (0, 1),
                (-1, -1),
                [colors.white, colors.HexColor('#f8fafc')],
            )
        )
    return pdf_style


@login_required
def exportar_cesta_basica_pdf_recibo(request, pk):
    """
    PDF para impressão do recibo: colunas até assinatura (espaço em branco), sem data.
    """
    lista = _get_lista_cesta_empresa(request, pk)
    comp = lista.competencia
    empresa = comp.empresa

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'cb_t',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=4,
        alignment=1,
    )
    sub_style = ParagraphStyle(
        'cb_sub',
        parent=styles['Normal'],
        fontSize=8,
        alignment=1,
        textColor=colors.HexColor('#334155'),
    )

    mes_titulo = f'{_mes_nome_pt(comp.mes).upper()} {comp.ano}'
    titulo_doc = f'RECIBO DE CESTA BÁSICA — {mes_titulo}'

    cell_txt, cell_num = _cell_styles_base(styles)
    cell_assin = ParagraphStyle(
        'cb_cell_assin',
        parent=cell_txt,
        fontName='Helvetica',
    )

    headers = ['№', 'EMPREGADO', 'FUNÇÃO', 'LOTAÇÃO', 'ASSINATURA']

    data_rows = [headers]
    for n, item in enumerate(_itens_export(lista), start=1):
        nome_txt = (item.nome_exibicao or '').strip() or '—'
        funcao_txt = (item.funcao or '').strip() or '—'
        lot_txt = (item.lotacao or '').strip() or '—'
        data_rows.append(
            [
                Paragraph(xml_escape(str(n)), cell_num),
                Paragraph(xml_escape(nome_txt), cell_txt),
                Paragraph(xml_escape(funcao_txt), cell_txt),
                Paragraph(xml_escape(lot_txt), cell_txt),
                Paragraph('', cell_assin),
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
        title=f'Cesta Básica Recibo {comp.referencia}',
    )

    nome_emp = _nome_empresa_pdf(empresa)
    story = [
        Paragraph(f'<b>{xml_escape(nome_emp)}</b>', title_style),
        Paragraph(
            f'Competência {comp.referencia} — {xml_escape(str(empresa))}',
            sub_style,
        ),
        Spacer(1, 4 * mm),
        Paragraph(f'<b>{titulo_doc}</b>', title_style),
        Spacer(1, 5 * mm),
    ]

    last_idx = len(data_rows) - 1
    _cw = (10, 56, 36, 36, 95)
    table = Table(data_rows, colWidths=[w * mm for w in _cw], repeatRows=1)
    table.setStyle(TableStyle(_table_style_base(last_idx)))
    story.append(table)

    decl = _texto_declaracao_padrao(lista)
    local_txt = (lista.local_emissao or 'PARNAMIRIM - RN').strip()
    rodape_data = f'{_data_rodape_pt(lista)}, {xml_escape(local_txt)}.'

    rodape_style = ParagraphStyle(
        'cb_rod',
        parent=styles['Normal'],
        fontSize=8,
        leading=11,
        spaceBefore=8,
        alignment=4,
    )
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(xml_escape(decl), rodape_style))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(f'<b>{rodape_data}</b>', rodape_style))

    doc.build(story)
    buf.seek(0)

    name = _safe_filename_part(lista.nome_exibicao)
    ref = f'{comp.mes:02d}_{comp.ano}'
    filename = f'CestaBasica_Recibo_{name}_{ref}.pdf'

    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@login_required
def exportar_cesta_basica_pdf_relatorio(request, pk):
    """
    PDF relatório: planilha com Recebeu (Sim/Não), data de recebimento; sem coluna assinatura.
    """
    lista = _get_lista_cesta_empresa(request, pk)
    comp = lista.competencia
    empresa = comp.empresa

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'cb_tr',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=4,
        alignment=1,
    )
    sub_style = ParagraphStyle(
        'cb_sub_r',
        parent=styles['Normal'],
        fontSize=8,
        alignment=1,
        textColor=colors.HexColor('#334155'),
    )

    cell_txt, cell_num = _cell_styles_base(styles)
    cell_center = ParagraphStyle(
        'cb_cell_c',
        parent=cell_txt,
        alignment=1,
        fontName='Helvetica',
    )

    headers = ['№', 'EMPREGADO', 'FUNÇÃO', 'LOTAÇÃO', 'RECEBEU', 'DATA RECEB.']

    data_rows = [headers]
    for n, item in enumerate(_itens_export(lista), start=1):
        nome_txt = (item.nome_exibicao or '').strip() or '—'
        funcao_txt = (item.funcao or '').strip() or '—'
        lot_txt = (item.lotacao or '').strip() or '—'
        recebeu_txt = 'Sim' if item.recebido else 'Não'
        if item.data_recebimento:
            data_txt = item.data_recebimento.strftime('%d/%m/%Y')
        else:
            data_txt = '—'
        data_rows.append(
            [
                Paragraph(xml_escape(str(n)), cell_num),
                Paragraph(xml_escape(nome_txt), cell_txt),
                Paragraph(xml_escape(funcao_txt), cell_txt),
                Paragraph(xml_escape(lot_txt), cell_txt),
                Paragraph(xml_escape(recebeu_txt), cell_center),
                Paragraph(xml_escape(data_txt), cell_center),
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
        title=f'Cesta Básica Relatório {comp.referencia}',
    )

    nome_emp = _nome_empresa_pdf(empresa)
    titulo_doc = f'RELATÓRIO DE ENTREGA — CESTA BÁSICA — {_mes_nome_pt(comp.mes).upper()} {comp.ano}'
    agora = timezone.localtime(timezone.now())
    emitido = agora.strftime('%d/%m/%Y %H:%M')

    story = [
        Paragraph(f'<b>{xml_escape(nome_emp)}</b>', title_style),
        Paragraph(
            f'{xml_escape(lista.nome_exibicao)} · Competência {comp.referencia} — {xml_escape(str(empresa))}',
            sub_style,
        ),
        Spacer(1, 4 * mm),
        Paragraph(f'<b>{titulo_doc}</b>', title_style),
        Spacer(1, 5 * mm),
    ]

    last_idx = len(data_rows) - 1
    _cw = (10, 48, 32, 32, 22, 26)
    table = Table(data_rows, colWidths=[w * mm for w in _cw], repeatRows=1)
    table.setStyle(TableStyle(_table_style_base(last_idx)))
    story.append(table)

    rodape_style = ParagraphStyle(
        'cb_rod_r',
        parent=styles['Normal'],
        fontSize=7,
        leading=10,
        spaceBefore=6,
        textColor=colors.HexColor('#64748b'),
        alignment=1,
    )
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            xml_escape(f'Documento para controle interno · Emitido em {emitido}'),
            rodape_style,
        )
    )

    doc.build(story)
    buf.seek(0)

    name = _safe_filename_part(lista.nome_exibicao)
    ref = f'{comp.mes:02d}_{comp.ano}'
    filename = f'CestaBasica_Relatorio_{name}_{ref}.pdf'

    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


# Compatibilidade: URL antiga aponta para o recibo
exportar_cesta_basica_pdf = exportar_cesta_basica_pdf_recibo
