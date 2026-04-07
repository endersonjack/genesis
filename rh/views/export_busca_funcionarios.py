"""
Exportação PDF e Excel dos resultados da busca avançada de funcionários.
Cabeçalho alinhado ao padrão Vale Transporte (logo + bloco de texto da empresa).
"""
import re
from io import BytesIO
from types import SimpleNamespace
from xml.sax.saxutils import escape as xml_escape

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from empresas.models import Empresa

from controles_rh.views.cesta_export import (
    PDF_LANDSCAPE_CONTENT_MM,
    _flowables_header_compact,
    _flowables_titulo_pdf_centro,
    _linha_extra_cabecalho_recibo,
    _nome_empresa_pdf,
    _unlink_temp_logo_paths,
)
from controles_rh.views.pdf_rodape import flowables_rodape_impressao

from .base import _empresa_ativa_or_redirect
from .funcionarios import queryset_funcionarios_busca_avancada


def _safe_filename_part(text):
    s = re.sub(r'[^\w\s\-]', '_', str(text), flags=re.UNICODE)
    s = re.sub(r'\s+', '_', s.strip())
    return (s[:60] or 'busca').strip('_')


def _header_text_html_busca_funcionarios(empresa, _comp, ctx):
    """Mesmo bloco textual que VT (nome fantasia, razão, linha de contexto, CNPJ/end/tel, e-mail)."""
    nome = _nome_empresa_pdf(empresa)
    bits = [f'<b>{xml_escape(nome)}</b>']
    razao = (empresa.razao_social or '').strip()
    if razao and razao.upper() != (nome or '').upper():
        bits.append(f'<font size="8" color="#64748b">{xml_escape(razao)}</font>')
    subtitulo = (getattr(ctx, 'subtitulo', None) or 'Busca de funcionários').strip()
    bits.append(xml_escape(subtitulo))
    extra = _linha_extra_cabecalho_recibo(empresa)
    if extra:
        bits.append(xml_escape(extra))
    email = (getattr(empresa, 'email', None) or '').strip()
    if email:
        bits.append(xml_escape(f'E-mail: {email}'))
    return '<br/>'.join(bits)


def _col_widths_pdf_mm():
    total = float(PDF_LANDSCAPE_CONTENT_MM)
    w = [8.0, 52.0, 24.0, 26.0, 46.0, 46.0, 75.0]
    s = sum(w)
    if abs(s - total) > 0.01:
        w[-1] = max(30.0, w[-1] + (total - s))
    return w


@login_required
def exportar_busca_funcionarios_pdf(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para exportar a busca.',
    )
    if redirect_response:
        return redirect_response

    empresa = Empresa.objects.get(pk=empresa_ativa.pk)
    qs = queryset_funcionarios_busca_avancada(request, empresa_ativa)
    funcionarios = list(qs)
    total = len(funcionarios)

    agora = timezone.localtime(timezone.now())
    ctx_header = SimpleNamespace(
        subtitulo=f'Busca de funcionários · Emitido em {agora.strftime("%d/%m/%Y %H:%M")}',
    )
    comp_dummy = SimpleNamespace(referencia='')

    styles = getSampleStyleSheet()
    headers = ['#', 'NOME', 'MATRÍCULA', 'CPF', 'CARGO', 'LOTAÇÃO', 'SITUAÇÃO']
    cw = _col_widths_pdf_mm()
    data_rows = [headers]
    for n, f in enumerate(funcionarios, start=1):
        data_rows.append(
            [
                str(n),
                (f.nome or '—').strip(),
                (f.matricula or '—').strip(),
                (f.cpf or '—').strip(),
                (f.cargo.nome if f.cargo else '—'),
                (f.lotacao.nome if f.lotacao else '—'),
                f.get_situacao_atual_display(),
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
        title='Busca de funcionários',
    )
    story = []
    temp_logo_paths = []
    story.extend(
        _flowables_header_compact(
            empresa,
            comp_dummy,
            ctx_header,
            styles,
            _header_text_html_busca_funcionarios,
            temp_logo_paths,
        )
    )
    titulo_doc = 'LISTAGEM — BUSCA DE FUNCIONÁRIOS'
    story.extend(_flowables_titulo_pdf_centro(titulo_doc, styles))

    meta_style = ParagraphStyle(
        'busca_meta',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6,
    )
    story.append(
        Paragraph(
            xml_escape(f'Total de registros: {total}'),
            meta_style,
        )
    )
    story.append(Spacer(1, 2 * mm))

    last_idx = len(data_rows) - 1
    table = Table(
        data_rows,
        colWidths=[w * mm for w in cw],
        repeatRows=1,
    )
    pdf_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dbeafe')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cbd5e1')),
    ]
    if last_idx >= 1:
        pdf_style.append(
            (
                'ROWBACKGROUNDS',
                (0, 1),
                (-1, -1),
                [colors.white, colors.HexColor('#f8fafc')],
            )
        )
    table.setStyle(TableStyle(pdf_style))
    story.append(table)
    story.extend(flowables_rodape_impressao(request, styles, space_before_mm=3))

    doc.build(story)
    _unlink_temp_logo_paths(temp_logo_paths)
    buf.seek(0)

    stamp = agora.strftime('%Y%m%d_%H%M')
    filename = f'Busca_funcionarios_{_safe_filename_part(empresa_ativa)}_{stamp}.pdf'
    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@login_required
def exportar_busca_funcionarios_xlsx(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para exportar a busca.',
    )
    if redirect_response:
        return redirect_response

    empresa = Empresa.objects.get(pk=empresa_ativa.pk)
    qs = queryset_funcionarios_busca_avancada(request, empresa_ativa)
    funcionarios = list(qs)
    total = len(funcionarios)

    headers = [
        '#',
        'Nome',
        'Matrícula',
        'CPF',
        'Cargo',
        'Lotação',
        'Situação',
    ]
    ncols = len(headers)

    wb = Workbook()
    ws = wb.active
    ws.title = 'Busca'

    row = 1
    if getattr(empresa, 'logo', None) and empresa.logo:
        try:
            with empresa.logo.open('rb') as f:
                xl_img = XLImage(BytesIO(f.read()))
            max_w = 220
            if xl_img.width > max_w:
                ratio = max_w / xl_img.width
                xl_img.width = max_w
                xl_img.height = int(xl_img.height * ratio)
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
            ws.add_image(xl_img, 'A1')
            ws.row_dimensions[row].height = max(50, min(xl_img.height * 0.78, 130))
            row += 1
        except Exception:
            pass

    agora = timezone.localtime(timezone.now())
    nome_pdf = _nome_empresa_pdf(empresa)
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
    c = ws.cell(
        row=row,
        column=1,
        value=f'{nome_pdf} — Busca de funcionários — Emitido em {agora.strftime("%d/%m/%Y %H:%M")}',
    )
    c.font = Font(bold=True, size=12)
    c.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    row += 1

    extra = _linha_extra_cabecalho_recibo(empresa)
    if extra:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
        c2 = ws.cell(row=row, column=1, value=extra)
        c2.font = Font(size=9)
        c2.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
        row += 1

    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
    c3 = ws.cell(row=row, column=1, value=f'Total de registros: {total}')
    c3.font = Font(bold=True, size=10)
    row += 1

    for col, h in enumerate(headers, 1):
        hc = ws.cell(row=row, column=col, value=h)
        hc.font = Font(bold=True)
        hc.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    row += 1

    for n, f in enumerate(funcionarios, start=1):
        valores = [
            n,
            (f.nome or '').strip(),
            (f.matricula or '').strip(),
            (f.cpf or '').strip(),
            (f.cargo.nome if f.cargo else ''),
            (f.lotacao.nome if f.lotacao else ''),
            f.get_situacao_atual_display(),
        ]
        for col, val in enumerate(valores, 1):
            ws.cell(row=row, column=col, value=val)
        row += 1

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    stamp = agora.strftime('%Y%m%d_%H%M')
    filename = f'Busca_funcionarios_{_safe_filename_part(empresa_ativa)}_{stamp}.xlsx'
    response = HttpResponse(
        buf.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
