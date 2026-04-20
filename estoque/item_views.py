from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.db.models import Case, Count, F, IntegerField, Max, Q, Value, When
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.registry import registrar_auditoria

from core.urlutils import redirect_empresa, reverse_empresa

from .exclusao_estoque import (
    descricao_com_sufixo_excluido,
    item_precisa_arquivar,
    listas_compra_com_item,
    requisicoes_com_item,
)
from .forms import ItemForm
from .models import (
    CategoriaItem,
    Ferramenta,
    Item,
    ItemImagem,
    RequisicaoEstoque,
    RequisicaoEstoqueItem,
)
try:
    from .item_etiqueta_pdf import build_item_etiqueta_pdf_bytes
except Exception:
    build_item_etiqueta_pdf_bytes = None
from .qr_item import (
    attach_auto_qrcode_to_item,
    parse_ferramenta_qr_payload,
    parse_item_qr_payload,
)

# Fallback inline: evita quebra do servidor se o módulo de etiqueta não estiver disponível.
def _fmt_decimal_br(val, casas: int) -> str:
    if val is None:
        return '—'
    try:
        v = Decimal(str(val))
    except Exception:
        return '—'
    tpl = f'{{:.{casas}f}}'
    s = tpl.format(v).rstrip('0').rstrip('.')
    return s.replace('.', ',')


def _etiqueta_item_pdf_bytes(item) -> bytes:
    import os
    import tempfile
    from io import BytesIO
    from xml.sax.saxutils import escape as xml_escape

    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
    from reportlab.platypus import Image as RLImage
    from reportlab.platypus import Paragraph, Table, TableStyle

    from .qr_item import build_item_qr_payload, generate_qr_png_bytes

    largura_doc = 178 * mm
    altura_doc = 62 * mm

    if item.qrcode_imagem:
        item.qrcode_imagem.open('rb')
        try:
            qr_data = item.qrcode_imagem.read()
        finally:
            item.qrcode_imagem.close()
    else:
        qr_data = generate_qr_png_bytes(build_item_qr_payload(item.empresa_id, item.pk))

    buf = BytesIO()
    inset_pt = 6
    frame = Frame(
        inset_pt,
        inset_pt,
        largura_doc - 2 * inset_pt,
        altura_doc - 2 * inset_pt,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        id='normal',
        showBoundary=0,
    )
    doc = BaseDocTemplate(buf, pagesize=(largura_doc, altura_doc))
    doc.addPageTemplates([PageTemplate(id='etq', frames=[frame])])

    w = frame._width
    h = frame._height
    # Segunda referência: QR ocupa ~40% da largura, texto ~60%; QR quadrado, centrado na faixa.
    col_qr = w * 0.40
    col_txt = max(w - col_qr, 10 * mm)
    qr_side = min(col_qr, h)

    styles = getSampleStyleSheet()
    st_compact = ParagraphStyle(
        'etq_cmp',
        parent=styles['Normal'],
        fontSize=12,
        leading=14,
        spaceBefore=0,
        spaceAfter=0,
        textColor=colors.HexColor('#0f172a'),
    )

    def bloco_linha(
        titulo: str,
        valor: str,
        *,
        bold: bool = False,
        tam_valor: int = 12,
        tam_titulo: int = 7,
    ) -> Paragraph:
        esc_t = xml_escape(titulo)
        esc_v = xml_escape(valor)
        fn_val = 'Helvetica-Bold' if bold else 'Helvetica'
        inner = (
            f'<font name="Helvetica-Bold" size="{tam_titulo}" color="#334155">{esc_t}</font>'
            f'<br/><font name="{fn_val}" size="{tam_valor}" color="#0f172a">{esc_v}</font>'
        )
        return Paragraph(inner, st_compact)

    def _caps_exibir(s: str) -> str:
        t = (s or '').strip()
        return t.upper() if t else '—'

    marca_txt = _caps_exibir(item.marca or '')
    qmin_txt = _fmt_decimal_br(item.quantidade_minima, 4)
    desc_txt = _caps_exibir(item.descricao or '')
    unidade_txt = _caps_exibir(item.unidade_medida.abreviada)
    comp = (getattr(item.unidade_medida, 'completa', None) or '').strip()
    if comp:
        unidade_txt = f'{unidade_txt} ({_caps_exibir(comp)})'

    linha_marca = Table([[bloco_linha('Marca', marca_txt)]], colWidths=[col_txt])
    # Unidade à direita, com coluna mais larga (texto tipo "UND (UNIDADE)").
    col_qtd = col_txt * 0.38
    col_un = col_txt - col_qtd
    linha_qtd_un = Table(
        [[bloco_linha('Qtd. mínima', qmin_txt), bloco_linha('Unidade', unidade_txt)]],
        colWidths=[col_qtd, col_un],
    )

    tbl_pad = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]
    linha_marca.setStyle(TableStyle(tbl_pad))
    linha_qtd_un.setStyle(TableStyle(tbl_pad))

    linha_gap = Paragraph(
        '&nbsp;',
        ParagraphStyle(
            'etq_gap',
            parent=st_compact,
            fontSize=1,
            leading=6,
            textColor=colors.HexColor('#ffffff'),
        ),
    )

    direita = Table(
        [
            [
                bloco_linha(
                    'Descrição',
                    desc_txt,
                    bold=True,
                    tam_valor=13,
                )
            ],
            [linha_marca],
            [linha_gap],
            [linha_qtd_un],
        ],
        colWidths=[col_txt],
    )
    direita.setStyle(TableStyle(tbl_pad))

    fd, tmp_png = tempfile.mkstemp(suffix='.png')
    try:
        with os.fdopen(fd, 'wb') as tmp_f:
            tmp_f.write(qr_data)
        qr_img = RLImage(tmp_png, width=qr_side, height=qr_side)
        qr_celula = Table(
            [[qr_img]],
            colWidths=[col_qr],
            rowHeights=[h],
            hAlign='LEFT',
        )
        qr_celula.setStyle(
            TableStyle(
                [
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ]
            )
        )
        principal = Table(
            [[qr_celula, direita]],
            colWidths=[col_qr, col_txt],
            rowHeights=[h],
            hAlign='LEFT',
        )
        estilo_principal = list(tbl_pad)
        estilo_principal.append(('VALIGN', (0, 0), (-1, -1), 'MIDDLE'))
        principal.setStyle(TableStyle(estilo_principal))
        doc.build([principal])
    finally:
        try:
            os.unlink(tmp_png)
        except OSError:
            pass

    return buf.getvalue()


def _etiqueta_pdf_bytes_para_item(item) -> bytes:
    if build_item_etiqueta_pdf_bytes:
        return build_item_etiqueta_pdf_bytes(item)
    return _etiqueta_item_pdf_bytes(item)


def _etiqueta_pdf_para_png_bytes(pdf_bytes: bytes, *, dpi: int = 300) -> bytes:
    """Rasteriza a primeira página do PDF em PNG (mesma arte da etiqueta)."""
    from io import BytesIO

    import fitz
    from PIL import Image

    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    try:
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
        buf = BytesIO()
        img.save(buf, format='PNG', optimize=True)
        return buf.getvalue()
    finally:
        doc.close()


# Auditoria de requisição sem linha de item / sem alteração de saldo (evita linhas “em branco” no log).
# Operações só de cautela ficam na página Relatórios (auditoria de cautelas).
_MOVIMENTAR_LOG_OPERACOES_EXCLUIDAS = frozenset(
    (
        'criar_requisicao',
        'editar_cabecalho',
        'cancelar_requisicao',
        'adiar_prazo',
        'entrega_completa',
        'entrega_parcial',
    )
)


def _empresa(request):
    return getattr(request, 'empresa_ativa', None)


def _is_htmx(request):
    v = request.headers.get('HX-Request')
    if v is None:
        v = request.META.get('HTTP_HX_REQUEST')
    return str(v).lower() == 'true'


def _movimentar_page_url(request, page_num: int) -> str:
    base = reverse_empresa(request, 'estoque:movimentar_estoque')
    q = request.GET.copy()
    q.pop('partial', None)
    if page_num <= 1:
        q.pop('page', None)
    else:
        q['page'] = str(page_num)
    if q:
        return f'{base}?{q.urlencode()}'
    return base


def _movimentar_pagination_items(request, page_obj):
    """Lista de dicts: num (int|None), url (str|''), current (bool), ellipsis (bool)."""
    paginator = page_obj.paginator
    total = paginator.num_pages
    cur = page_obj.number
    if total <= 1:
        return []
    window = 2
    if total <= (window * 2 + 3):
        nums = list(range(1, total + 1))
    else:
        nums = [1]
        start = max(2, cur - window)
        end = min(total - 1, cur + window)
        if start > 2:
            nums.append(None)
        nums.extend(range(start, end + 1))
        if end < total - 1:
            nums.append(None)
        nums.append(total)
    items = []
    for n in nums:
        if n is None:
            items.append({'ellipsis': True, 'num': None, 'url': '', 'current': False})
        else:
            items.append(
                {
                    'ellipsis': False,
                    'num': n,
                    'url': _movimentar_page_url(request, n),
                    'current': n == cur,
                }
            )
    return items


def _parse_decimal_mov_log(val):
    if val is None or val == '':
        return None
    try:
        return Decimal(str(val))
    except InvalidOperation:
        return None


def _movimentar_log_resolve_requisicao_pk(d, req_existentes, item_para_req):
    """
    Retorna o pk de RequisicaoEstoque para montar URL de detalhe, ou None se
    a requisição não existir mais (ex.: excluída) e não houver fallback válido.
    """
    raw = d.get('requisicao_id')
    if raw is not None:
        try:
            rpk = int(raw)
            if rpk in req_existentes:
                return rpk
        except (TypeError, ValueError):
            pass
    riid = d.get('requisicao_item_id')
    if riid is not None:
        try:
            rpk = item_para_req.get(int(riid))
            if rpk is not None and rpk in req_existentes:
                return rpk
        except (TypeError, ValueError):
            pass
    return None


def _enriquecer_logs_movimentacao(request, empresa, logs_page_obj):
    """
    Anexa em cada RegistroAuditoria atributos usados em _movimentar_log.html
    (rótulo de item, quantidade, classificação da ação e URL da requisição).
    """
    if not logs_page_obj:
        return
    obj_list = getattr(logs_page_obj, 'object_list', None)
    if not obj_list:
        return

    item_ids = set()
    for log in obj_list:
        d = log.detalhes or {}
        if d.get('item_descricao'):
            continue
        raw_id = d.get('item_id')
        if raw_id is None:
            continue
        try:
            item_ids.add(int(raw_id))
        except (TypeError, ValueError):
            pass

    desc_por_item = {}
    if item_ids:
        for row in Item.objects.filter(
            pk__in=item_ids, empresa=empresa
        ).only('pk', 'descricao'):
            desc_por_item[row.pk] = row.descricao

    rids = set()
    ri_ids = set()
    for log in obj_list:
        d = log.detalhes or {}
        raw = d.get('requisicao_id')
        if raw is not None:
            try:
                rids.add(int(raw))
            except (TypeError, ValueError):
                pass
        raw_i = d.get('requisicao_item_id')
        if raw_i is not None:
            try:
                ri_ids.add(int(raw_i))
            except (TypeError, ValueError):
                pass

    item_para_req = {
        row['pk']: row['requisicao_id']
        for row in RequisicaoEstoqueItem.objects.filter(
            pk__in=ri_ids,
            requisicao__empresa=empresa,
        ).values('pk', 'requisicao_id')
    }
    req_from_items = set(item_para_req.values())
    candidatos_req = rids | req_from_items
    req_existentes = set(
        RequisicaoEstoque.objects.filter(
            empresa=empresa, pk__in=candidatos_req
        ).values_list('pk', flat=True)
    )

    for log in obj_list:
        d = log.detalhes or {}
        op = d.get('operacao') or ''

        desc = d.get('item_descricao')
        if not desc:
            raw_id = d.get('item_id')
            if raw_id is not None:
                try:
                    desc = desc_por_item.get(int(raw_id))
                except (TypeError, ValueError):
                    pass
        log.mov_item_label = desc or '—'

        delta = _parse_decimal_mov_log(d.get('delta'))

        qtd_disp = None
        if op not in ('criar_requisicao', 'editar_cabecalho'):
            qdv = d.get('quantidade_devolvida')
            if qdv not in (None, ''):
                qtd_disp = qdv
            elif d.get('quantidade') not in (None, ''):
                qtd_disp = d.get('quantidade')
            elif delta is not None and op in (
                'ajuste_por_edicao_requisicao',
                'ajustar_quantidade',
            ):
                if delta != 0:
                    qtd_disp = str(abs(delta))

        log.mov_qtd_label = qtd_disp if qtd_disp not in (None, '') else '—'

        saldo = d.get('saldo_depois')
        log.mov_saldo_label = saldo if saldo not in (None, '') else '—'

        rid = d.get('requisicao_id')
        req_pk_resolvido = _movimentar_log_resolve_requisicao_pk(
            d, req_existentes, item_para_req
        )
        req_url = None
        if req_pk_resolvido is not None:
            try:
                req_url = reverse_empresa(
                    request,
                    'estoque:detalhe_requisicao',
                    kwargs={'pk': req_pk_resolvido},
                )
            except (TypeError, ValueError):
                pass
        log.mov_req_url = req_url

        kind = 'outro'
        if op == 'adicionar' and rid is None:
            kind = 'manual_add'
        elif op == 'retirar' and rid is None:
            kind = 'manual_ret'
        elif rid is not None and op == 'retirar':
            kind = 'req_retirada'
        elif rid is not None and op in (
            'devolver_total',
            'devolver_parcial',
            'devolver_por_exclusao_requisicao',
            'devolver_por_cancelamento_requisicao',
        ):
            kind = 'req_devolucao'
        elif rid is not None and op in (
            'ajuste_por_edicao_requisicao',
            'ajustar_quantidade',
        ):
            if delta is not None and delta > 0:
                kind = 'req_retirada'
            elif delta is not None and delta < 0:
                kind = 'req_devolucao'
        elif rid is not None and op in (
            'criar_requisicao',
            'editar_cabecalho',
            'cancelar_requisicao',
        ):
            kind = 'req_meta'

        log.mov_acao_kind = kind


def _hx_redirect_lista(request, lista_viewname: str):
    resp = HttpResponse(status=200)
    resp['HX-Redirect'] = reverse_empresa(request, lista_viewname)
    return resp


def _anexar_imagens_novas(item, files_list):
    if not files_list:
        return
    agg = item.imagens.aggregate(m=Max('ordem'))
    nxt = (agg['m'] if agg['m'] is not None else -1) + 1
    tinha_padrao = item.imagens.filter(padrao=True).exists()
    for i, f in enumerate(files_list):
        ItemImagem.objects.create(item=item, imagem=f, ordem=nxt + i)
    if not tinha_padrao:
        _garantir_uma_imagem_padrao(item)


def _garantir_uma_imagem_padrao(item):
    """Se não houver imagem marcada como padrão, marca a primeira da ordem."""
    qs = ItemImagem.objects.filter(item=item).order_by('ordem', 'pk')
    imgs = list(qs)
    if not imgs:
        return
    if sum(1 for im in imgs if im.padrao) == 1:
        return
    if sum(1 for im in imgs if im.padrao) > 1:
        keep = next(im for im in imgs if im.padrao)
        ItemImagem.objects.filter(item=item, padrao=True).exclude(pk=keep.pk).update(
            padrao=False
        )
        return
    imgs[0].padrao = True
    imgs[0].save(update_fields=['padrao'])


def _item_com_imagens_prefetch(item, empresa):
    return get_object_or_404(
        Item.objects.prefetch_related('imagens'),
        pk=item.pk,
        empresa=empresa,
    )


def _render_item_form_modal(request, item, form):
    if item is None:
        post_url = reverse_empresa(request, 'estoque:modal_novo_item')
        titulo_modal = 'Novo item'
        excluir_url = None
    else:
        post_url = reverse_empresa(
            request, 'estoque:modal_editar_item', kwargs={'pk': item.pk}
        )
        titulo_modal = f'Editar — {item.descricao[:80]}'
        excluir_url = reverse_empresa(
            request, 'estoque:modal_excluir_item', kwargs={'pk': item.pk}
        )
    return render(
        request,
        'estoque/partials/item_form_modal.html',
        {
            'form': form,
            'post_url': post_url,
            'titulo_modal': titulo_modal,
            'item': item,
            'excluir_url': excluir_url,
        },
    )


def _modal_item_form(request, item):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:lista_itens')

    if item is not None:
        item = get_object_or_404(
            Item.objects.prefetch_related('imagens'),
            pk=item.pk,
            empresa=empresa,
        )

    if request.method == 'POST':
        if item is not None:
            form = ItemForm(
                request.POST,
                request.FILES,
                instance=item,
                empresa=empresa,
                lock_quantidade_estoque=True,
                lock_qrcode_imagem=True,
            )
        else:
            form = ItemForm(
                request.POST,
                request.FILES,
                empresa=empresa,
                lock_quantidade_estoque=True,
                lock_qrcode_imagem=True,
            )
        if form.is_valid():
            saved = form.save()
            attach_auto_qrcode_to_item(saved)
            if item is None:
                registrar_auditoria(
                    request,
                    acao='create',
                    resumo=f'Item «{saved.descricao[:80]}» cadastrado.',
                    modulo='estoque',
                    detalhes={'item_id': saved.pk},
                )
                messages.success(request, 'Item cadastrado.')
            else:
                registrar_auditoria(
                    request,
                    acao='update',
                    resumo=f'Item «{saved.descricao[:80]}» atualizado.',
                    modulo='estoque',
                    detalhes={'item_id': saved.pk},
                )
                messages.success(request, 'Item atualizado.')
            return _hx_redirect_lista(request, 'estoque:lista_itens')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        if item is not None:
            form = ItemForm(
                instance=item,
                empresa=empresa,
                lock_quantidade_estoque=True,
                lock_qrcode_imagem=True,
            )
        else:
            form = ItemForm(
                empresa=empresa,
                lock_quantidade_estoque=True,
                lock_qrcode_imagem=True,
            )
        preselect_categoria = (request.GET.get('preselect_categoria') or '').strip()
        if preselect_categoria.isdigit() and 'categoria' in form.fields:
            form.fields['categoria'].initial = int(preselect_categoria)

    return _render_item_form_modal(request, item, form)


@login_required
def lista_itens(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    q = (request.GET.get('q') or '').strip()
    itens = (
        Item.objects.filter(empresa=empresa, ativo=True)
        .select_related('categoria', 'unidade_medida', 'fornecedor')
        .prefetch_related('imagens')
        .order_by('descricao')
    )
    if q:
        itens = itens.filter(
            Q(descricao__icontains=q)
            | Q(marca__icontains=q)
            | Q(categoria__nome__icontains=q)
        )
    ctx = {
        'page_title': 'Itens',
        'itens': itens,
        'q': q,
    }
    if _is_htmx(request):
        return render(request, 'estoque/itens/_lista_conteudo.html', ctx)
    return render(request, 'estoque/itens/lista.html', ctx)


TODO_ESTOQUE_ITENS_POR_PAGINA = 20

TODO_ESTOQUE_SORT_COLUMNS = frozenset(
    {
        'descricao',
        'categoria',
        'unidade',
        'peso',
        'preco',
        'saldo',
        'minimo',
        'situacao',
    }
)


def _todo_estoque_sort_url(request, column: str) -> str:
    """Alterna asc/desc se a coluna já for a ativa; reseta página para 1."""
    base = reverse_empresa(request, 'estoque:todo_estoque')
    qp = request.GET.copy()
    qp.pop('partial', None)
    cur_o = (qp.get('ordem') or 'descricao').strip()
    cur_d = (qp.get('dir') or 'asc').strip().lower()
    if cur_d not in ('asc', 'desc'):
        cur_d = 'asc'
    if cur_o not in TODO_ESTOQUE_SORT_COLUMNS:
        cur_o = 'descricao'
    if column == cur_o:
        new_d = 'desc' if cur_d == 'asc' else 'asc'
    else:
        new_d = 'asc'
    qp['ordem'] = column
    qp['dir'] = new_d
    qp.pop('page', None)
    if qp:
        return f'{base}?{qp.urlencode()}'
    return base


def _todo_estoque_apply_order(itens, ordem: str, dir_: str):
    """Aplica ordenação estável (desempate por descrição)."""
    desc = dir_ == 'desc'
    if ordem == 'situacao':
        itens = itens.annotate(
            _ord_situacao=Case(
                When(quantidade_estoque__lte=0, then=Value(0)),
                When(
                    quantidade_minima__gt=0,
                    quantidade_estoque__lt=F('quantidade_minima'),
                    then=Value(1),
                ),
                When(
                    quantidade_minima__gt=0,
                    quantidade_estoque=F('quantidade_minima'),
                    then=Value(2),
                ),
                default=Value(3),
                output_field=IntegerField(),
            )
        )
        primary = (
            F('_ord_situacao').desc(nulls_last=True)
            if desc
            else F('_ord_situacao').asc(nulls_last=True)
        )
        return itens.order_by(primary, 'descricao')
    if ordem == 'categoria':
        primary = (
            F('categoria__nome').desc(nulls_last=True)
            if desc
            else F('categoria__nome').asc(nulls_last=True)
        )
        return itens.order_by(primary, 'descricao')
    if ordem == 'unidade':
        primary = (
            F('unidade_medida__abreviada').desc(nulls_last=True)
            if desc
            else F('unidade_medida__abreviada').asc(nulls_last=True)
        )
        return itens.order_by(primary, 'descricao')
    if ordem == 'peso':
        primary = F('peso').desc(nulls_last=True) if desc else F('peso').asc(nulls_last=True)
        return itens.order_by(primary, 'descricao')
    if ordem == 'preco':
        primary = F('preco').desc(nulls_last=True) if desc else F('preco').asc(nulls_last=True)
        return itens.order_by(primary, 'descricao')
    if ordem == 'saldo':
        primary = (
            F('quantidade_estoque').desc(nulls_last=True)
            if desc
            else F('quantidade_estoque').asc(nulls_last=True)
        )
        return itens.order_by(primary, 'descricao')
    if ordem == 'minimo':
        primary = (
            F('quantidade_minima').desc(nulls_last=True)
            if desc
            else F('quantidade_minima').asc(nulls_last=True)
        )
        return itens.order_by(primary, 'descricao')
    # descricao (default)
    primary = F('descricao').desc(nulls_last=True) if desc else F('descricao').asc(nulls_last=True)
    return itens.order_by(primary, 'descricao')


def _todo_estoque_page_url(request, page_num: int) -> str:
    base = reverse_empresa(request, 'estoque:todo_estoque')
    q = request.GET.copy()
    q.pop('partial', None)
    if page_num <= 1:
        q.pop('page', None)
    else:
        q['page'] = str(page_num)
    if q:
        return f'{base}?{q.urlencode()}'
    return base


def _todo_estoque_pagination_items(request, page_obj):
    """Mesmo padrão de _movimentar_pagination_items, para a página Todo o estoque."""
    paginator = page_obj.paginator
    total = paginator.num_pages
    cur = page_obj.number
    if total <= 1:
        return []
    window = 2
    if total <= (window * 2 + 3):
        nums = list(range(1, total + 1))
    else:
        nums = [1]
        start = max(2, cur - window)
        end = min(total - 1, cur + window)
        if start > 2:
            nums.append(None)
        nums.extend(range(start, end + 1))
        if end < total - 1:
            nums.append(None)
        nums.append(total)
    items = []
    for n in nums:
        if n is None:
            items.append({'ellipsis': True, 'num': None, 'url': '', 'current': False})
        else:
            items.append(
                {
                    'ellipsis': False,
                    'num': n,
                    'url': _todo_estoque_page_url(request, n),
                    'current': n == cur,
                }
            )
    return items


@login_required
def todo_estoque(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    # Pedido HTMX: só resultados. Link copiado sem HTMX deve renderizar a página completa.
    if request.GET.get('partial') == 'todo' and not _is_htmx(request):
        qp = request.GET.copy()
        qp.pop('partial', None)
        base = reverse_empresa(request, 'estoque:todo_estoque')
        if qp:
            return redirect(f'{base}?{qp.urlencode()}')
        return redirect(base)

    q = (request.GET.get('q') or '').strip()
    categoria_raw = (request.GET.get('categoria') or '').strip()
    situacao = (request.GET.get('situacao') or '').strip()
    ordem_raw = (request.GET.get('ordem') or 'descricao').strip()
    dir_raw = (request.GET.get('dir') or 'asc').strip().lower()
    if dir_raw not in ('asc', 'desc'):
        dir_raw = 'asc'
    if ordem_raw not in TODO_ESTOQUE_SORT_COLUMNS:
        ordem_raw = 'descricao'

    listar_todos = q.lower() == '#todos'

    itens = (
        Item.objects.filter(empresa=empresa, ativo=True)
        .select_related('categoria', 'unidade_medida')
        .prefetch_related('imagens')
    )

    if q and not listar_todos:
        itens = itens.filter(
            Q(descricao__icontains=q)
            | Q(marca__icontains=q)
            | Q(categoria__nome__icontains=q)
        )

    if categoria_raw.isdigit():
        itens = itens.filter(categoria_id=int(categoria_raw))

    if situacao == 'atencao':
        itens = itens.filter(
            Q(quantidade_estoque=0) | Q(quantidade_estoque__lt=F('quantidade_minima'))
        )
    elif situacao == 'zerado':
        itens = itens.filter(quantidade_estoque__lte=0)
    elif situacao == 'abaixo_min':
        itens = itens.filter(
            quantidade_estoque__gt=0,
            quantidade_minima__gt=0,
            quantidade_estoque__lt=F('quantidade_minima'),
        )

    itens = _todo_estoque_apply_order(itens, ordem_raw, dir_raw)

    categorias = CategoriaItem.objects.filter(empresa=empresa).order_by('nome')

    # Resumo por categoria (itens ativos).
    resumo_por_categoria = list(
        CategoriaItem.objects.filter(empresa=empresa)
        .annotate(
            qtd_itens=Count(
                'itens',
                filter=Q(itens__empresa=empresa, itens__ativo=True),
            )
        )
        .order_by('-qtd_itens', 'nome')
    )

    paginator = Paginator(itens, TODO_ESTOQUE_ITENS_POR_PAGINA)
    page_param = request.GET.get('page') or 1
    try:
        page_obj = paginator.page(page_param)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    ctx = {
        'page_title': 'Todo o estoque',
        'todo_itens_por_pagina': TODO_ESTOQUE_ITENS_POR_PAGINA,
        'todo_ordem': ordem_raw,
        'todo_dir': dir_raw,
        'todo_sort': {col: _todo_estoque_sort_url(request, col) for col in sorted(TODO_ESTOQUE_SORT_COLUMNS)},
        'page_obj': page_obj,
        'q': q,
        'categoria_filtro': categoria_raw if categoria_raw.isdigit() else '',
        'situacao_filtro': situacao,
        'categorias': categorias,
        'todo_url_prev': (
            _todo_estoque_page_url(request, page_obj.previous_page_number())
            if page_obj.has_previous()
            else None
        ),
        'todo_url_next': (
            _todo_estoque_page_url(request, page_obj.next_page_number())
            if page_obj.has_next()
            else None
        ),
        'todo_pagination_items': _todo_estoque_pagination_items(request, page_obj),
        'resumo_por_categoria': resumo_por_categoria,
    }
    if _is_htmx(request) or request.GET.get('partial') == 'todo':
        return render(request, 'estoque/_todo_estoque_resultados.html', ctx)
    return render(request, 'estoque/todo_estoque.html', ctx)


@login_required
def movimentar_estoque(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    # Pedido vindo do formulário HTMX inclui partial=movimentar; visita direta à URL copiada
    # não deve mostrar só o fragmento — redireciona sem o parâmetro.
    if request.GET.get('partial') == 'movimentar' and not _is_htmx(request):
        qp = request.GET.copy()
        qp.pop('partial', None)
        base = reverse_empresa(request, 'estoque:movimentar_estoque')
        if qp:
            return redirect(f'{base}?{qp.urlencode()}')
        return redirect(base)

    q = (request.GET.get('q') or '').strip()
    categoria_raw = (request.GET.get('categoria') or '').strip()
    situacao = (request.GET.get('situacao') or '').strip()
    listar_todos = q.lower() == '#todos'

    # Sem filtros: lista vazia (use a busca). Com texto, categoria ou situação: itens ativos filtrados.
    # Busca exata "#todos" lista todos os itens ativos da empresa (ainda respeita categoria/situação).
    busca_expandida = bool(q) or categoria_raw.isdigit() or bool(situacao)

    itens = (
        Item.objects.filter(empresa=empresa, ativo=True)
        .select_related('categoria', 'unidade_medida')
        .prefetch_related('imagens')
        .order_by('descricao')
    )
    if not busca_expandida:
        itens = itens.none()

    if q and not listar_todos:
        itens = itens.filter(
            Q(descricao__icontains=q)
            | Q(marca__icontains=q)
            | Q(categoria__nome__icontains=q)
        )

    if categoria_raw.isdigit():
        itens = itens.filter(categoria_id=int(categoria_raw))

    if situacao == 'zerado':
        itens = itens.filter(quantidade_estoque__lte=0)
    elif situacao == 'abaixo_min':
        itens = itens.filter(
            quantidade_estoque__gt=0,
            quantidade_minima__gt=0,
            quantidade_estoque__lt=F('quantidade_minima'),
        )
    elif situacao == 'atencao':
        itens = itens.filter(
            Q(quantidade_estoque=0)
            | Q(quantidade_estoque__lt=F('quantidade_minima'))
        )

    categorias = CategoriaItem.objects.filter(empresa=empresa).order_by('nome')

    paginator = Paginator(itens, 20)
    page_param = request.GET.get('page') or 1
    try:
        page_obj = paginator.page(page_param)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    ctx = {
        'page_title': 'Movimentar estoque',
        'page_obj': page_obj,
        'q': q,
        'categoria_filtro': categoria_raw if categoria_raw.isdigit() else '',
        'situacao_filtro': situacao,
        'movimentar_busca_expandida': busca_expandida,
        'categorias': categorias,
        'movimentar_url_prev': (
            _movimentar_page_url(request, page_obj.previous_page_number())
            if page_obj.has_previous()
            else None
        ),
        'movimentar_url_next': (
            _movimentar_page_url(request, page_obj.next_page_number())
            if page_obj.has_next()
            else None
        ),
        'movimentar_pagination_items': _movimentar_pagination_items(request, page_obj),
    }
    if _is_htmx(request) or request.GET.get('partial') == 'movimentar':
        return render(request, 'estoque/itens/_movimentar_conteudo.html', ctx)
    return render(request, 'estoque/itens/movimentar.html', ctx)


def _render_movimentar_saldo_modal(
    request,
    item,
    *,
    errors=(),
    operacao='retirar',
    quantidade_val='',
):
    post_url = reverse_empresa(
        request, 'estoque:modal_movimentar_saldo', kwargs={'pk': item.pk}
    )
    return render(
        request,
        'estoque/partials/movimentar_saldo_modal.html',
        {
            'item': item,
            'post_url': post_url,
            'errors': errors,
            'operacao': operacao if operacao in ('adicionar', 'retirar') else 'retirar',
            'quantidade_val': quantidade_val,
        },
    )


@login_required
def modal_movimentar_saldo(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item = get_object_or_404(
        Item.objects.select_related('unidade_medida'),
        pk=pk,
        empresa=empresa,
        ativo=True,
    )

    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:movimentar_estoque')

    if request.method == 'POST':
        operacao = (request.POST.get('operacao') or '').strip()
        qty_raw = (request.POST.get('quantidade') or '').strip().replace(',', '.')
        errors = []

        if operacao not in ('adicionar', 'retirar'):
            errors.append('Operação inválida.')

        qty = None
        if not qty_raw:
            errors.append('Informe a quantidade.')
        else:
            try:
                qty = Decimal(qty_raw)
            except InvalidOperation:
                errors.append('Quantidade inválida.')
                qty = None

        if qty is not None:
            if qty <= 0:
                errors.append('Informe uma quantidade maior que zero.')
            else:
                exp = qty.as_tuple().exponent
                if isinstance(exp, int) and exp < -4:
                    errors.append('Use no máximo 4 casas decimais.')

        if not errors and qty is not None:
            with transaction.atomic():
                locked = Item.objects.select_for_update().get(
                    pk=item.pk, empresa=empresa, ativo=True
                )
                saldo_antes = locked.quantidade_estoque
                if operacao == 'retirar':
                    if qty > saldo_antes:
                        errors.append(
                            'Não é possível retirar mais do que o saldo atual.'
                        )
                    else:
                        locked.quantidade_estoque = saldo_antes - qty
                else:
                    locked.quantidade_estoque = saldo_antes + qty

                if not errors:
                    try:
                        locked.full_clean()
                    except ValidationError as exc:
                        if exc.error_dict:
                            for msgs in exc.error_dict.values():
                                errors.extend(str(m) for m in msgs)
                        else:
                            errors.extend(str(m) for m in exc.error_list)
                        if not errors:
                            errors.append('Não foi possível salvar o saldo.')

                if not errors:
                    locked.save(update_fields=['quantidade_estoque'])
                    saldo_depois = locked.quantidade_estoque
                    registrar_auditoria(
                        request,
                        acao='update',
                        resumo=(
                            f'Estoque «{locked.descricao[:80]}»: '
                            f'{operacao} {qty} ({saldo_antes} → {saldo_depois}).'
                        ),
                        modulo='estoque',
                        detalhes={
                            'item_id': locked.pk,
                            'item_descricao': locked.descricao[:120],
                            'operacao': operacao,
                            'quantidade': str(qty),
                            'saldo_antes': str(saldo_antes),
                            'saldo_depois': str(saldo_depois),
                        },
                    )
                    messages.success(request, 'Estoque atualizado.')
                    resp = HttpResponse(status=200)
                    resp['HX-Redirect'] = (
                        request.headers.get('HX-Current-URL')
                        or reverse_empresa(request, 'estoque:movimentar_estoque')
                    )
                    return resp

        return _render_movimentar_saldo_modal(
            request,
            item,
            errors=errors,
            operacao=operacao,
            quantidade_val=request.POST.get('quantidade') or '',
        )

    return _render_movimentar_saldo_modal(request, item)


@login_required
def modal_novo_item(request):
    return _modal_item_form(request, None)


@login_required
def modal_editar_item(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    item = get_object_or_404(Item, pk=pk, empresa=empresa)
    return _modal_item_form(request, item)


@login_required
def modal_adicionar_imagens_item(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    item = get_object_or_404(Item, pk=pk, empresa=empresa)
    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:detalhes_item', pk=pk)
    if request.method == 'POST':
        files = request.FILES.getlist('imagens')
        if not files:
            messages.error(request, 'Selecione ao menos uma imagem.')
            response = render(
                request,
                'estoque/itens/modal_adicionar_imagens.html',
                {'item': item},
            )
            response['HX-Retarget'] = '#modal-content'
            response['HX-Reswap'] = 'innerHTML'
            return response
        _anexar_imagens_novas(item, files)
        messages.success(request, 'Imagens adicionadas.')
        item = _item_com_imagens_prefetch(item, empresa)
        return render(
            request,
            'estoque/itens/_detalhes_imagens_card.html',
            {'item': item},
        )
    return render(
        request,
        'estoque/itens/modal_adicionar_imagens.html',
        {'item': item},
    )


@login_required
def modal_gerar_qrcode_item(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item = get_object_or_404(
        Item.objects.prefetch_related('imagens'),
        pk=pk,
        empresa=empresa,
    )

    if request.method != 'POST':
        return redirect_empresa(request, 'estoque:detalhes_item', pk=pk)

    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:detalhes_item', pk=pk)

    if item.qrcode_imagem:
        messages.info(request, 'Este item já possui QR Code.')
    else:
        from django.conf import settings

        ok, err = attach_auto_qrcode_to_item(item)
        item.refresh_from_db()
        if ok and item.qrcode_imagem:
            messages.success(request, 'QR Code gerado.')
        else:
            msg = 'Não foi possível gerar o QR Code. Tente de novo.'
            if settings.DEBUG and err:
                msg = f'{msg} ({err})'
            messages.warning(request, msg)

    item.refresh_from_db()
    return render(
        request,
        'estoque/itens/_detalhes_qrcode_card.html',
        {'item': item},
    )


@login_required
def modal_excluir_qrcode_item(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item = get_object_or_404(
        Item.objects.prefetch_related('imagens'),
        pk=pk,
        empresa=empresa,
    )

    if request.method != 'POST':
        return redirect_empresa(request, 'estoque:detalhes_item', pk=pk)

    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:detalhes_item', pk=pk)

    if item.qrcode_imagem:
        item.qrcode_imagem.delete(save=False)
        item.save(update_fields=['qrcode_imagem'])
        messages.success(
            request,
            'QR Code removido. Use «Gerar QR Code» para criar outro.',
        )
    else:
        messages.info(request, 'Este item não tinha QR Code.')

    item.refresh_from_db()
    return render(
        request,
        'estoque/itens/_detalhes_qrcode_card.html',
        {'item': item},
    )


@login_required
def modal_excluir_item(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item = get_object_or_404(Item, pk=pk, empresa=empresa)
    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:item_excluir', kwargs={'pk': pk})

    if item_precisa_arquivar(item):
        resp = HttpResponse(status=200)
        resp['HX-Redirect'] = reverse_empresa(
            request, 'estoque:item_excluir', kwargs={'pk': pk}
        )
        return resp

    return render(
        request,
        'estoque/partials/item_excluir_modal.html',
        {
            'item': item,
            'excluir_url': reverse_empresa(
                request, 'estoque:item_excluir', kwargs={'pk': pk}
            ),
            'voltar_editar_url': reverse_empresa(
                request, 'estoque:modal_editar_item', kwargs={'pk': pk}
            ),
        },
    )


@login_required
def leitor_estoque_resolve(request):
    """Resolve texto lido pelo leitor 2D (QR) para item ou ferramenta da empresa ativa."""
    empresa = _empresa(request)
    if not empresa:
        return JsonResponse({'ok': False, 'error': 'empresa'}, status=400)
    raw = request.GET.get('c') or ''
    parsed = parse_item_qr_payload(raw)
    if parsed:
        eid, iid = parsed
        if eid != empresa.pk:
            return JsonResponse({'ok': False, 'error': 'empresa'}, status=403)
        if not Item.objects.filter(pk=iid, empresa_id=empresa.pk).exists():
            return JsonResponse({'ok': False, 'error': 'not_found'}, status=404)
        detail_url = reverse_empresa(
            request, 'estoque:detalhes_item', kwargs={'pk': iid}
        )
        return JsonResponse({'ok': True, 'kind': 'item', 'item_id': iid, 'detail_url': detail_url})

    parsed_f = parse_ferramenta_qr_payload(raw)
    if parsed_f:
        eid, fid = parsed_f
        if eid != empresa.pk:
            return JsonResponse({'ok': False, 'error': 'empresa'}, status=403)
        if not Ferramenta.objects.filter(pk=fid, empresa_id=empresa.pk).exists():
            return JsonResponse({'ok': False, 'error': 'not_found'}, status=404)
        detail_url = reverse_empresa(
            request, 'estoque:detalhes_ferramenta', kwargs={'pk': fid}
        )
        return JsonResponse(
            {
                'ok': True,
                'kind': 'ferramenta',
                'ferramenta_id': fid,
                'detail_url': detail_url,
            }
        )

    return JsonResponse({'ok': False, 'error': 'invalid'}, status=400)


@login_required
def item_novo(request):
    return redirect_empresa(request, 'estoque:lista_itens')


@login_required
def imprimir_etiqueta_item(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    item = get_object_or_404(
        Item.objects.select_related('unidade_medida'),
        pk=pk,
        empresa=empresa,
    )
    data = _etiqueta_pdf_bytes_para_item(item)
    resp = HttpResponse(data, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="etiqueta_item_{item.pk}.pdf"'
    return resp


@login_required
def imprimir_etiqueta_item_png(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    item = get_object_or_404(
        Item.objects.select_related('unidade_medida'),
        pk=pk,
        empresa=empresa,
    )
    try:
        pdf_bytes = _etiqueta_pdf_bytes_para_item(item)
        png_bytes = _etiqueta_pdf_para_png_bytes(pdf_bytes)
    except ImportError:
        messages.error(
            request,
            'Exportação em PNG não está disponível (dependência PyMuPDF ausente).',
        )
        return redirect_empresa(request, 'estoque:detalhes_item', kwargs={'pk': pk})
    resp = HttpResponse(png_bytes, content_type='image/png')
    resp['Content-Disposition'] = (
        f'inline; filename="etiqueta_item_{item.pk}.png"'
    )
    return resp


@login_required
def detalhes_item(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    item = get_object_or_404(
        Item.objects.select_related('categoria', 'unidade_medida', 'fornecedor').prefetch_related(
            'imagens'
        ),
        pk=pk,
        empresa=empresa,
    )
    return render(
        request,
        'estoque/itens/detalhes.html',
        {
            'page_title': item.descricao[:120],
            'item': item,
        },
    )


@login_required
def item_editar(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    get_object_or_404(Item, pk=pk, empresa=empresa)
    return redirect_empresa(request, 'estoque:detalhes_item', pk=pk)


@login_required
def item_imagem_excluir(request, item_pk, imagem_pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item = get_object_or_404(Item, pk=item_pk, empresa=empresa)
    img = get_object_or_404(ItemImagem, pk=imagem_pk, item=item)
    if request.method == 'POST':
        img.imagem.delete(save=False)
        img.delete()
        messages.success(request, 'Imagem removida.')
        _garantir_uma_imagem_padrao(item)
        item = _item_com_imagens_prefetch(item, empresa)
        if _is_htmx(request):
            return render(
                request,
                'estoque/itens/_detalhes_imagens_card.html',
                {'item': item},
            )
        return redirect_empresa(request, 'estoque:detalhes_item', pk=item.pk)

    return redirect_empresa(request, 'estoque:detalhes_item', pk=item.pk)


@login_required
def item_imagem_definir_padrao(request, item_pk, imagem_pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    item = get_object_or_404(Item, pk=item_pk, empresa=empresa)
    imagem = get_object_or_404(ItemImagem, pk=imagem_pk, item=item)
    if request.method != 'POST':
        return redirect_empresa(request, 'estoque:detalhes_item', pk=item.pk)
    with transaction.atomic():
        ItemImagem.objects.filter(item=item).update(padrao=False)
        imagem.padrao = True
        imagem.save(update_fields=['padrao'])
    messages.success(request, 'Imagem padrão para visualização atualizada.')
    item = _item_com_imagens_prefetch(item, empresa)
    if _is_htmx(request):
        return render(
            request,
            'estoque/itens/_detalhes_imagens_card.html',
            {'item': item},
        )
    return redirect_empresa(request, 'estoque:detalhes_item', pk=item.pk)


@login_required
def item_excluir(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    item = get_object_or_404(Item, pk=pk, empresa=empresa)
    requisicoes_v = requisicoes_com_item(item)
    listas_v = listas_compra_com_item(item)
    tem_vinculos = bool(requisicoes_v or listas_v)

    if request.method == 'POST':
        if tem_vinculos:
            if request.POST.get('confirmar_arquivamento') != '1':
                messages.error(
                    request,
                    'Marque a confirmação para arquivar este item com vínculos.',
                )
            else:
                with transaction.atomic():
                    locked = Item.objects.select_for_update().get(
                        pk=item.pk, empresa=empresa
                    )
                    desc_antes = locked.descricao[:120]
                    nova = descricao_com_sufixo_excluido(
                        locked.descricao,
                        Item._meta.get_field('descricao').max_length,
                    )
                    locked.descricao = nova
                    locked.ativo = False
                    locked.save(update_fields=['descricao', 'ativo'])
                registrar_auditoria(
                    request,
                    acao='update',
                    resumo=(
                        f'Item arquivado (excluído lógico): «{desc_antes}» → «{nova[:120]}».'
                    ),
                    modulo='estoque',
                    detalhes={'item_id': locked.pk, 'arquivado': True},
                )
                messages.success(
                    request,
                    'Item arquivado: o nome passou a incluir «(EXCLUÍDO)» e o cadastro '
                    'ficou inativo, preservando requisições e listas vinculadas.',
                )
                if _is_htmx(request):
                    return _hx_redirect_lista(request, 'estoque:lista_itens')
                return redirect_empresa(request, 'estoque:lista_itens')
        else:
            desc = item.descricao[:120]
            iid = item.pk
            for img in list(item.imagens.all()):
                img.imagem.delete(save=False)
                img.delete()
            if item.qrcode_imagem:
                item.qrcode_imagem.delete(save=False)
            item.delete()
            registrar_auditoria(
                request,
                acao='delete',
                resumo=f'Item «{desc}» excluído.',
                modulo='estoque',
                detalhes={'item_id': iid},
            )
            messages.success(request, 'Item excluído.')
            if _is_htmx(request):
                return _hx_redirect_lista(request, 'estoque:lista_itens')
            return redirect_empresa(request, 'estoque:lista_itens')

    nova_desc_prev = descricao_com_sufixo_excluido(
        item.descricao,
        Item._meta.get_field('descricao').max_length,
    )
    return render(
        request,
        'estoque/itens/excluir.html',
        {
            'page_title': 'Excluir item',
            'item': item,
            'tem_vinculos': tem_vinculos,
            'requisicoes_vinculadas': requisicoes_v,
            'listas_compra_vinculadas': listas_v,
            'nova_descricao_prevista': nova_desc_prev,
        },
    )
