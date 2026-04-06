import re
from io import BytesIO
from xml.sax.saxutils import escape as xml_escape

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from controles_rh.models import CestaBasicaItem
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


def cesta_basica_item_para_linha_vt(vt_item):
    """
    Encontra a linha de Cesta Básica na mesma competência do VT (por funcionário ou nome).
    Se houver várias listas, usa a primeira linha encontrada (ordem de lista).
    """
    competencia = vt_item.tabela.competencia
    qs = CestaBasicaItem.objects.filter(lista__competencia=competencia).select_related(
        'funcionario', 'lista'
    )
    if vt_item.funcionario_id:
        return qs.filter(funcionario_id=vt_item.funcionario_id).order_by('lista_id', 'id').first()
    nome = (vt_item.nome or '').strip() or (vt_item.nome_exibicao or '').strip()
    if not nome:
        return None
    return qs.filter(
        Q(nome__iexact=nome) | Q(funcionario__nome__iexact=nome)
    ).order_by('lista_id', 'id').first()


def vt_recibo_cesta_sets_por_recebimento(tabela, itens_list):
    """
    Para a planilha VT: duas classes de linhas com correspondência na Cesta Básica
    (mesma competência, mesmo critério de `cesta_basica_item_para_linha_vt`).

    Retorna (pks_recebido, pks_nao_recebido):
    - pks_recebido: pode imprimir o recibo individual (botão azul).
    - pks_nao_recebido: tem linha na CB mas ainda não recebeu (botão desabilitado).
    Linhas sem correspondência na CB não entram em nenhum dos conjuntos.
    """
    comp = tabela.competencia
    cesta_items = list(
        CestaBasicaItem.objects.filter(lista__competencia=comp)
        .select_related('funcionario')
        .order_by('lista_id', 'id')
    )
    by_func = {}
    by_name = {}
    for ci in cesta_items:
        if ci.funcionario_id and ci.funcionario_id not in by_func:
            by_func[ci.funcionario_id] = ci
        nome = (ci.nome or '').strip()
        if not nome and ci.funcionario_id:
            nome = (ci.funcionario.nome or '').strip()
        key = nome.lower() if nome else ''
        if key and key not in by_name:
            by_name[key] = ci
    recebido_ok = set()
    pendente = set()
    for vt in itens_list:
        ci = None
        if vt.funcionario_id and vt.funcionario_id in by_func:
            ci = by_func[vt.funcionario_id]
        else:
            nome = (vt.nome or '').strip() or (vt.nome_exibicao or '').strip()
            if nome and nome.lower() in by_name:
                ci = by_name[nome.lower()]
        if not ci:
            continue
        if ci.recebido:
            recebido_ok.add(vt.pk)
        else:
            pendente.add(vt.pk)
    return recebido_ok, pendente


def _http_response_pdf_recibo_cesta(lista, items, *, filename_label=None):
    """
    Gera o PDF de recibo (modelo colunas + declaração) para as linhas informadas.
    filename_label: parte do nome do arquivo; default = nome da lista.
    """
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
    for n, item in enumerate(items, start=1):
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
    rodape_data = f'{_rodape_data_recibo_pdf(lista, items)}, {xml_escape(local_txt)}.'

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
    return _http_response_pdf_recibo_cesta(lista, items)


@login_required
def exportar_recibo_cesta_individual_por_vt_item(request, vt_item_pk):
    """
    Recibo de Cesta Básica com uma única linha, a partir da linha do VT correspondente
    (mesmo funcionário ou mesmo nome na competência).
    """
    from controles_rh.views.vale_transporte import _get_item_vt_empresa

    vt_item = _get_item_vt_empresa(request, vt_item_pk)
    cesta_item = cesta_basica_item_para_linha_vt(vt_item)
    if not cesta_item:
        raise Http404(
            'Não há linha correspondente na Cesta Básica desta competência. '
            'Inclua o empregado em uma lista de Cesta Básica.'
        )
    if not cesta_item.recebido:
        raise PermissionDenied(
            'O recibo individual só pode ser impresso depois de marcar '
            '"Recebeu" na Cesta Básica para este empregado.'
        )
    lista = cesta_item.lista
    _get_lista_cesta_empresa(request, lista.pk)
    return _http_response_pdf_recibo_cesta(
        lista,
        [cesta_item],
        filename_label=cesta_item.nome_exibicao,
    )


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
    )


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
