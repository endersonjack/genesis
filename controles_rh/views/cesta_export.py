import logging
import os
import re
import tempfile
from io import BytesIO
from typing import List, Optional
from xml.sax.saxutils import escape as xml_escape

from PIL import Image as PILImage
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from controles_rh.views.cesta_basica import _get_lista_cesta_empresa
from controles_rh.views.pdf_rodape import flowables_rodape_impressao
from empresas.models import Empresa

logger = logging.getLogger(__name__)

# Largura útil em paisagem A4 com margens laterais iguais (mm)
PDF_LANDSCAPE_CONTENT_MM = 277


def _col_widths_recibo_mm():
    """
    Colunas №, empregado, função e lotação no mínimo prático; o restante fica para ASSINATURA.
    Empregado com largura suficiente para nomes longos em uma linha (com redução de fonte se preciso).
    """
    w_n, w_e, w_f, w_l = 6, 52, 20, 20
    w_a = PDF_LANDSCAPE_CONTENT_MM - (w_n + w_e + w_f + w_l)
    return (w_n, w_e, w_f, w_l, w_a)


def _paragraph_empregado_nome_uma_linha(nome_txt, parent_style, col_w_mm, pad_each_side_pt):
    """
    Nome em negrito, maiúsculo, sem quebra de linha: reduz a fonte até caber na largura útil.
    Espaços viram NBSP para o Paragraph do ReportLab não quebrar no meio do nome.
    """
    font = 'Helvetica-Bold'
    max_w = max(1.0, col_w_mm * mm - 2 * pad_each_side_pt)
    size = 7.5
    while size > 1.5 and stringWidth(nome_txt, font, size) > max_w:
        size -= 0.25
    size = max(size, 1.5)
    st = ParagraphStyle(
        'cb_nom1',
        parent=parent_style,
        fontName=font,
        fontSize=size,
        leading=size * 1.1,
        spaceBefore=0,
        spaceAfter=0,
    )
    safe = xml_escape(nome_txt).replace(' ', '\xa0')
    return Paragraph(safe, st)


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


def _logo_bytes_normalizados_para_reportlab(raw: bytes) -> bytes:
    """
    CMYK/paleta → RGB; PNG opaco (transparência em fundo branco) para o PDF incorporar sempre.
    """
    pil = PILImage.open(BytesIO(raw))
    if pil.mode == 'CMYK':
        pil = pil.convert('RGB')
    elif pil.mode in ('P', 'PA'):
        pil = pil.convert('RGBA')
    elif pil.mode not in ('RGB', 'RGBA', 'L'):
        pil = pil.convert('RGB')
    if pil.mode == 'L':
        pil = pil.convert('RGB')
    if pil.mode == 'RGBA':
        bg = PILImage.new('RGB', pil.size, (255, 255, 255))
        bg.paste(pil, mask=pil.split()[3])
        pil = bg
    out = BytesIO()
    pil.save(out, format='PNG', optimize=True)
    return out.getvalue()


def _unlink_temp_logo_paths(paths: Optional[List[str]]) -> None:
    if not paths:
        return
    for p in paths:
        try:
            os.unlink(p)
        except OSError:
            pass


def _read_empresa_logo_raw_bytes(empresa) -> Optional[bytes]:
    """Lê o arquivo do logo via storage; fallback para caminho local no disco."""
    if not getattr(empresa, 'logo', None) or not empresa.logo.name:
        return None
    try:
        with empresa.logo.open('rb') as f:
            return f.read()
    except Exception:
        logger.debug(
            'Logo pk=%s: falha ao abrir via storage; tentando path local',
            getattr(empresa, 'pk', None),
            exc_info=True,
        )
    path_attr = getattr(empresa.logo, 'path', None)
    if path_attr and os.path.isfile(path_attr):
        try:
            with open(path_attr, 'rb') as f:
                return f.read()
        except OSError:
            logger.exception(
                'Logo pk=%s: leitura direta falhou em %s',
                getattr(empresa, 'pk', None),
                path_attr,
            )
    return None


def _empresa_logo_flowable(
    empresa,
    max_w_mm=44,
    max_h_mm=22,
    temp_paths: Optional[List[str]] = None,
):
    """
    Imagem redimensionada para o cabeçalho do PDF, ou None.

    Grava PNG em arquivo temporário e passa o *path* ao ReportLab: com BytesIO o
    carregamento lazy costuma falhar (imagem em branco) em algumas versões.
    """
    raw = _read_empresa_logo_raw_bytes(empresa)
    if not raw:
        return None
    path = None
    try:
        img_bytes = _logo_bytes_normalizados_para_reportlab(raw)
        pil = PILImage.open(BytesIO(img_bytes))
        w, h = pil.size
        if w <= 0 or h <= 0:
            return None
        max_w = float(max_w_mm * mm)
        max_h = float(max_h_mm * mm)
        scale = min(max_w / float(w), max_h / float(h), 1.0)
        rw = float(w) * scale
        rh = float(h) * scale
        if rw < 1 or rh < 1:
            return None
        fd, path = tempfile.mkstemp(suffix='.png', prefix='genesis_logo_')
        try:
            os.write(fd, img_bytes)
        finally:
            os.close(fd)
        if temp_paths is not None:
            temp_paths.append(path)
        return RLImage(path, width=rw, height=rh)
    except Exception:
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass
        logger.exception(
            'Falha ao montar logo da empresa no PDF (pk=%s)', getattr(empresa, 'pk', None)
        )
        return None


def _celula_placeholder_logo_mm(logo_w_mm, logo_h_mm):
    """Área vazia à esquerda quando não há arquivo de logo (mantém o layout duas colunas)."""
    w = logo_w_mm * mm
    h = logo_h_mm * mm
    t = Table([['']], colWidths=[w], rowHeights=[h])
    t.setStyle(
        TableStyle(
            [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOX', (0, 0), (-1, -1), 0.35, colors.HexColor('#e2e8f0')),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ]
        )
    )
    return t


def _story_chunks_logo_empresa(
    empresa,
    content_width_mm=PDF_LANDSCAPE_CONTENT_MM,
    temp_logo_paths: Optional[List[str]] = None,
):
    """Trechos a inserir no topo do PDF: logo centralizada + espaço (uso genérico)."""
    logo = _empresa_logo_flowable(empresa, temp_paths=temp_logo_paths)
    if not logo:
        return []
    tbl = Table([[logo]], colWidths=[content_width_mm * mm])
    tbl.setStyle(
        TableStyle(
            [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]
        )
    )
    return [tbl, Spacer(1, 3 * mm)]


def _header_text_html_recibo(empresa, comp, lista):
    """Bloco de texto do cabeçalho (sem título do documento — este vai separado e centralizado)."""
    nome = _nome_empresa_pdf(empresa)
    bits = [f'<b>{xml_escape(nome)}</b>']
    razao = (empresa.razao_social or '').strip()
    if razao and razao.upper() != (nome or '').upper():
        bits.append(f'<font size="8" color="#64748b">{xml_escape(razao)}</font>')
    bits.append(xml_escape(f'Competência {comp.referencia} · {lista.nome_exibicao}'))
    extra = _linha_extra_cabecalho_recibo(empresa)
    if extra:
        bits.append(xml_escape(extra))
    email = (getattr(empresa, 'email', None) or '').strip()
    if email:
        bits.append(xml_escape(f'E-mail: {email}'))
    return '<br/>'.join(bits)


def _header_text_html_relatorio(empresa, comp, lista):
    nome = _nome_empresa_pdf(empresa)
    bits = [f'<b>{xml_escape(nome)}</b>']
    razao = (empresa.razao_social or '').strip()
    if razao and razao.upper() != (nome or '').upper():
        bits.append(f'<font size="8" color="#64748b">{xml_escape(razao)}</font>')
    bits.append(xml_escape(f'{lista.nome_exibicao} · Competência {comp.referencia}'))
    extra = _linha_extra_cabecalho_recibo(empresa)
    if extra:
        bits.append(xml_escape(extra))
    email = (getattr(empresa, 'email', None) or '').strip()
    if email:
        bits.append(xml_escape(f'E-mail: {email}'))
    return '<br/>'.join(bits)


def _header_text_html_vt(empresa, comp, tabela):
    """Cabeçalho PDF Vale Transporte (mesmo padrão de bloco que recibo/relatório de cesta)."""
    nome = _nome_empresa_pdf(empresa)
    bits = [f'<b>{xml_escape(nome)}</b>']
    razao = (empresa.razao_social or '').strip()
    if razao and razao.upper() != (nome or '').upper():
        bits.append(f'<font size="8" color="#64748b">{xml_escape(razao)}</font>')
    nome_tabela = (getattr(tabela, 'nome', None) or '').strip() or 'Tabela VT'
    bits.append(xml_escape(f'{nome_tabela} · Competência {comp.referencia}'))
    extra = _linha_extra_cabecalho_recibo(empresa)
    if extra:
        bits.append(xml_escape(extra))
    email = (getattr(empresa, 'email', None) or '').strip()
    if email:
        bits.append(xml_escape(f'E-mail: {email}'))
    return '<br/>'.join(bits)


def _flowables_header_compact(
    empresa,
    comp,
    lista,
    styles,
    header_html_fn,
    temp_logo_paths: Optional[List[str]] = None,
):
    """
    Cabeçalho em duas colunas: imagem da empresa à esquerda, dados à direita.
    Sem logo, mantém uma área reservada à esquerda para o layout não colapsar em uma coluna só.
    """
    hdr_style = ParagraphStyle(
        'cb_hdr_compact',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        alignment=0,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=0,
        spaceBefore=0,
    )
    p = Paragraph(header_html_fn(empresa, comp, lista), hdr_style)

    logo_w_mm = 34
    logo_h_mm = 24
    gap_esq = 3 * mm
    logo_w = logo_w_mm * mm
    cw = PDF_LANDSCAPE_CONTENT_MM * mm
    text_w = cw - logo_w

    logo_img = _empresa_logo_flowable(
        empresa,
        max_w_mm=logo_w_mm,
        max_h_mm=logo_h_mm,
        temp_paths=temp_logo_paths,
    )
    if logo_img:
        col_esq = logo_img
    else:
        col_esq = _celula_placeholder_logo_mm(logo_w_mm, logo_h_mm)

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
    return [tbl, Spacer(1, 2 * mm)]


def _pdf_linha_mult(lista):
    """Multiplicador (0,7–1,8) a partir de recibo_altura_linha_pct (70–180)."""
    try:
        v = int(getattr(lista, 'recibo_altura_linha_pct', None) or 100)
    except (TypeError, ValueError):
        v = 100
    v = max(70, min(180, v))
    return v / 100.0


def _flowables_titulo_pdf_centro(titulo_doc, styles):
    """Título do documento centralizado, separado do cabeçalho com empresa/logo."""
    t = ParagraphStyle(
        'cb_titulo_doc_pdf',
        parent=styles['Normal'],
        fontSize=12,
        leading=14,
        alignment=1,
        spaceBefore=0,
        spaceAfter=0,
        textColor=colors.HexColor('#0f172a'),
        fontName='Helvetica-Bold',
    )
    return [
        Spacer(1, 6 * mm),
        Paragraph(f'<b>{xml_escape(titulo_doc)}</b>', t),
        Spacer(1, 5 * mm),
    ]


def _linha_extra_cabecalho_recibo(empresa):
    """Segunda linha do subtítulo do PDF (CNPJ, endereço, telefone)."""
    parts = []
    cnpj = (getattr(empresa, 'cnpj', None) or '').strip()
    if cnpj:
        parts.append(f'CNPJ: {cnpj}')
    end = (getattr(empresa, 'endereco', None) or '').strip()
    if end:
        parts.append(end)
    tel = (getattr(empresa, 'telefone', None) or '').strip()
    if tel:
        parts.append(f'Tel: {tel}')
    return ' · '.join(parts) if parts else ''


def _subtitulo_pdf_html_com_cnpj(linha1: str, empresa) -> str:
    """HTML para Paragraph: linha1 + opcional CNPJ · end · tel (preferências da empresa)."""
    extra = _linha_extra_cabecalho_recibo(empresa)
    if extra:
        return f'{xml_escape(linha1)}<br/>{xml_escape(extra)}'
    return xml_escape(linha1)


def _local_emissao_efetivo(lista):
    lo = (lista.local_emissao or '').strip()
    if lo:
        return lo
    return 'PARNAMIRIM - RN'


def _texto_declaracao_padrao(lista):
    if (lista.texto_declaracao or '').strip():
        return lista.texto_declaracao.strip()
    empresa = lista.competencia.empresa
    nome = _nome_empresa_pdf(empresa)
    return (
        f'DECLARO QUE RECEBI DA {nome.upper()}, NA DATA ABAIXO, A CESTA BÁSICA DE ALIMENTOS.'
    )


def _data_rodape_pt(lista):
    if lista.data_emissao_recibo:
        d = lista.data_emissao_recibo
        return f'{d.day:02d} DE {_mes_nome_pt(d.month).upper()} DE {d.year}'
    return '___ DE ______________ DE ______'


def _data_texto_rodape_de_date(d):
    """Formata uma data (date) como no rodapé do recibo (ex.: 05 DE ABRIL DE 2026)."""
    if not d:
        return None
    return f'{d.day:02d} DE {_mes_nome_pt(d.month).upper()} DE {d.year}'


def _rodape_data_recibo_pdf(lista, items):
    """
    Data exibida no rodapé do recibo em PDF.
    Recibo com uma linha: usa a mesma data da coluna «Data recebimento» (item.data_recebimento).
    Recibo com várias linhas: mantém a data da lista (data_emissao_recibo) ou placeholder.
    """
    items = list(items) if items is not None else []
    if len(items) == 1:
        dr = getattr(items[0], 'data_recebimento', None)
        texto = _data_texto_rodape_de_date(dr)
        if texto:
            return texto
    return _data_rodape_pt(lista)


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


def _cell_styles_recibo_tabela(styles, mult=1.0):
    """Células com quebra de linha; `mult` vem do slider de altura de linha na lista."""
    m = float(mult)
    cell_txt = ParagraphStyle(
        'cb_cell_txt_r',
        parent=styles['Normal'],
        fontSize=7.5,
        leading=9 * m,
        spaceBefore=0,
        spaceAfter=0,
    )
    cell_num = ParagraphStyle(
        'cb_cell_num_r',
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


def _table_style_compact(last_idx):
    """Menos padding interno para aproveitar melhor a folha."""
    return _table_style_compact_scaled(last_idx, 1.0)


def _table_style_compact_scaled(last_idx, mult=1.0):
    """Padding da tabela escalado pelo slider de altura de linha."""
    m = float(mult)
    pdf_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dbeafe')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2 * m),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2 * m),
        ('LEFTPADDING', (0, 0), (-1, -1), 3 * m),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3 * m),
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


def _table_style_recibo_assinatura(last_idx, mult=1.0):
    """Recibo com coluna ASSINATURA mais alta (~1,5 linha) para assinar à mão."""
    m = float(mult)
    base = _table_style_compact_scaled(last_idx, m)
    extra = [
        ('VALIGN', (4, 1), (4, -1), 'TOP'),
        ('TOPPADDING', (4, 1), (4, -1), 4 * m),
        ('BOTTOMPADDING', (4, 1), (4, -1), 12 * m),
        # Menos padding horizontal nas colunas estreitas; ainda separado o suficiente da grade
        ('LEFTPADDING', (0, 0), (-1, -1), 2 * m),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2 * m),
    ]
    return base + extra


def _http_response_pdf_recibo_cesta(lista, items, *, filename_label=None, request=None):
    """
    Gera o PDF de recibo (modelo colunas + declaração) para as linhas informadas.
    filename_label: parte do nome do arquivo; default = nome da lista.
    """
    comp = lista.competencia
    empresa = Empresa.objects.get(pk=comp.empresa_id)

    styles = getSampleStyleSheet()

    mes_titulo = f'{_mes_nome_pt(comp.mes).upper()} {comp.ano}'
    titulo_doc = f'RECIBO DE CESTA BÁSICA — {mes_titulo}'

    mult = _pdf_linha_mult(lista)
    cell_txt, cell_num = _cell_styles_recibo_tabela(styles, mult)
    # Altura útil ~1,5 linhas (base 13,5 pt) para assinatura à mão, escalada pelo slider
    cell_assin = ParagraphStyle(
        'cb_cell_assin',
        parent=cell_txt,
        fontName='Helvetica',
        leading=13.5 * mult,
        spaceBefore=0,
        spaceAfter=0,
    )
    headers = ['№', 'EMPREGADO', 'FUNÇÃO', 'LOTAÇÃO', 'ASSINATURA']

    _cw = _col_widths_recibo_mm()
    pad_nome = 2 * mult

    data_rows = [headers]
    for n, item in enumerate(items, start=1):
        nome_txt = ((item.nome_exibicao or '').strip() or '—').upper()
        funcao_txt = (item.funcao or '').strip() or '—'
        lot_txt = (item.lotacao or '').strip() or '—'
        # Uma quebra + leading 13,5 pt ≈ linha e meia em branco para assinar
        assin_bloco = Paragraph('<br/>', cell_assin)
        p_nome = _paragraph_empregado_nome_uma_linha(
            nome_txt, cell_txt, _cw[1], pad_nome
        )
        data_rows.append(
            [
                Paragraph(xml_escape(str(n)), cell_num),
                p_nome,
                Paragraph(xml_escape(funcao_txt), cell_txt),
                Paragraph(xml_escape(lot_txt), cell_txt),
                assin_bloco,
            ]
        )

    buf = BytesIO()
    margin = 10 * mm
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        title=f'Cesta Básica Recibo {comp.referencia}',
    )

    story = []
    temp_logo_paths: List[str] = []
    story.extend(
        _flowables_header_compact(
            empresa,
            comp,
            lista,
            styles,
            _header_text_html_recibo,
            temp_logo_paths=temp_logo_paths,
        )
    )
    story.extend(_flowables_titulo_pdf_centro(titulo_doc, styles))

    last_idx = len(data_rows) - 1
    table = Table(data_rows, colWidths=[w * mm for w in _cw], repeatRows=1)
    table.setStyle(TableStyle(_table_style_recibo_assinatura(last_idx, mult)))
    story.append(table)

    decl = _texto_declaracao_padrao(lista)
    local_txt = _local_emissao_efetivo(lista)
    rodape_data = f'{_rodape_data_recibo_pdf(lista, items)}, {xml_escape(local_txt)}.'

    rodape_style = ParagraphStyle(
        'cb_rod',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        spaceBefore=3,
        alignment=4,
    )
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(xml_escape(decl), rodape_style))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(f'<b>{rodape_data}</b>', rodape_style))
    story.extend(flowables_rodape_impressao(request, styles))

    doc.build(story)
    _unlink_temp_logo_paths(temp_logo_paths)
    buf.seek(0)

    label = filename_label if filename_label is not None else lista.nome_exibicao
    name = _safe_filename_part(label)
    ref = f'{comp.mes:02d}_{comp.ano}'
    filename = f'CestaBasica_Recibo_{name}_{ref}.pdf'

    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@login_required
def exportar_cesta_basica_pdf_recibo(request, pk):
    """
    PDF para impressão do recibo: colunas até assinatura (espaço em branco), sem data.
    """
    lista = _get_lista_cesta_empresa(request, pk)
    items = list(_itens_export(lista))
    return _http_response_pdf_recibo_cesta(lista, items, request=request)


@login_required
def exportar_recibo_cesta_individual_por_item(request, pk):
    """
    Recibo de Cesta Básica com uma única linha, a partir do item da própria lista (tela Cesta Básica).
    """
    from controles_rh.views.cesta_basica import _get_item_cesta_empresa

    item = _get_item_cesta_empresa(request, pk)
    if not item.recebido:
        raise PermissionDenied(
            'O recibo individual só pode ser impresso depois de marcar '
            '"Recebeu" para esta linha.'
        )
    lista = item.lista
    _get_lista_cesta_empresa(request, lista.pk)
    return _http_response_pdf_recibo_cesta(
        lista,
        [item],
        filename_label=item.nome_exibicao,
        request=request,
    )


@login_required
def exportar_cesta_basica_pdf_relatorio(request, pk):
    """
    PDF relatório: planilha com Recebeu (Sim/Não), data de recebimento; sem coluna assinatura.
    """
    lista = _get_lista_cesta_empresa(request, pk)
    comp = lista.competencia
    empresa = Empresa.objects.get(pk=comp.empresa_id)

    styles = getSampleStyleSheet()

    mult = _pdf_linha_mult(lista)
    cell_txt, cell_num = _cell_styles_recibo_tabela(styles, mult)
    cell_center = ParagraphStyle(
        'cb_cell_c',
        parent=cell_txt,
        alignment=1,
        fontName='Helvetica',
    )
    headers = ['№', 'EMPREGADO', 'FUNÇÃO', 'LOTAÇÃO', 'RECEBEU', 'DATA RECEB.']

    _cw = (8, 86, 46, 46, 24, 67)
    pad_nome_rel = 3 * mult

    data_rows = [headers]
    for n, item in enumerate(_itens_export(lista), start=1):
        nome_txt = ((item.nome_exibicao or '').strip() or '—').upper()
        funcao_txt = (item.funcao or '').strip() or '—'
        lot_txt = (item.lotacao or '').strip() or '—'
        recebeu_txt = 'Sim' if item.recebido else 'Não'
        if item.data_recebimento:
            data_txt = item.data_recebimento.strftime('%d/%m/%Y')
        else:
            data_txt = '—'
        p_nome = _paragraph_empregado_nome_uma_linha(
            nome_txt, cell_txt, _cw[1], pad_nome_rel
        )
        data_rows.append(
            [
                Paragraph(xml_escape(str(n)), cell_num),
                p_nome,
                Paragraph(xml_escape(funcao_txt), cell_txt),
                Paragraph(xml_escape(lot_txt), cell_txt),
                Paragraph(xml_escape(recebeu_txt), cell_center),
                Paragraph(xml_escape(data_txt), cell_center),
            ]
        )

    buf = BytesIO()
    margin = 10 * mm
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        title=f'Cesta Básica Relatório {comp.referencia}',
    )

    titulo_doc = f'RELATÓRIO DE ENTREGA — CESTA BÁSICA — {_mes_nome_pt(comp.mes).upper()} {comp.ano}'

    story = []
    temp_logo_paths: List[str] = []
    story.extend(
        _flowables_header_compact(
            empresa,
            comp,
            lista,
            styles,
            _header_text_html_relatorio,
            temp_logo_paths=temp_logo_paths,
        )
    )
    story.extend(_flowables_titulo_pdf_centro(titulo_doc, styles))

    last_idx = len(data_rows) - 1
    table = Table(data_rows, colWidths=[w * mm for w in _cw], repeatRows=1)
    table.setStyle(TableStyle(_table_style_compact_scaled(last_idx, mult)))
    story.append(table)

    story.extend(flowables_rodape_impressao(request, styles, space_before_mm=3))

    doc.build(story)
    _unlink_temp_logo_paths(temp_logo_paths)
    buf.seek(0)

    name = _safe_filename_part(lista.nome_exibicao)
    ref = f'{comp.mes:02d}_{comp.ano}'
    filename = f'CestaBasica_Relatorio_{name}_{ref}.pdf'

    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


# Compatibilidade: URL antiga aponta para o recibo
exportar_cesta_basica_pdf = exportar_cesta_basica_pdf_recibo
