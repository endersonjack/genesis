from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.registry import registrar_auditoria

from core.urlutils import redirect_empresa, reverse_empresa

from .exclusao_estoque import (
    cautelas_com_ferramenta,
    descricao_com_sufixo_excluido,
    ferramenta_precisa_arquivar,
)
from .forms import FerramentaForm
from .item_views import _etiqueta_pdf_para_png_bytes
from .models import Cautela, Entrega_Cautela, Ferramenta, FerramentaImagem
from .qr_item import (
    attach_auto_qrcode_to_ferramenta,
    build_ferramenta_qr_payload,
    generate_qr_png_bytes,
)


def _empresa(request):
    return getattr(request, 'empresa_ativa', None)


def _is_htmx(request):
    v = request.headers.get('HX-Request')
    if v is None:
        v = request.META.get('HTTP_HX_REQUEST')
    return str(v).lower() == 'true'


def _hx_redirect_lista(request, lista_viewname: str):
    resp = HttpResponse(status=200)
    resp['HX-Redirect'] = reverse_empresa(request, lista_viewname)
    return resp


def _anexar_imagens_novas(ferramenta, files_list):
    if not files_list:
        return
    agg = ferramenta.imagens.aggregate(m=Max('ordem'))
    nxt = (agg['m'] if agg['m'] is not None else -1) + 1
    tinha_padrao = ferramenta.imagens.filter(padrao=True).exists()
    for i, f in enumerate(files_list):
        FerramentaImagem.objects.create(ferramenta=ferramenta, imagem=f, ordem=nxt + i)
    if not tinha_padrao:
        _garantir_uma_imagem_padrao_ferramenta(ferramenta)


def _garantir_uma_imagem_padrao_ferramenta(ferramenta):
    qs = FerramentaImagem.objects.filter(ferramenta=ferramenta).order_by('ordem', 'pk')
    imgs = list(qs)
    if not imgs:
        return
    if sum(1 for im in imgs if im.padrao) == 1:
        return
    if sum(1 for im in imgs if im.padrao) > 1:
        keep = next(im for im in imgs if im.padrao)
        FerramentaImagem.objects.filter(ferramenta=ferramenta, padrao=True).exclude(
            pk=keep.pk
        ).update(padrao=False)
        return
    imgs[0].padrao = True
    imgs[0].save(update_fields=['padrao'])


def _ferramenta_com_imagens_prefetch(ferramenta, empresa):
    return get_object_or_404(
        Ferramenta.objects.prefetch_related('imagens'),
        pk=ferramenta.pk,
        empresa=empresa,
    )


def _etiqueta_ferramenta_pdf_bytes(ferramenta) -> bytes:
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

    largura_doc = 178 * mm
    altura_doc = 62 * mm

    if ferramenta.qrcode_imagem:
        ferramenta.qrcode_imagem.open('rb')
        try:
            qr_data = ferramenta.qrcode_imagem.read()
        finally:
            ferramenta.qrcode_imagem.close()
    else:
        qr_data = generate_qr_png_bytes(
            build_ferramenta_qr_payload(ferramenta.empresa_id, ferramenta.pk)
        )

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
    col_qr = w * 0.40
    col_txt = max(w - col_qr, 10 * mm)
    qr_side = min(col_qr, h)

    styles = getSampleStyleSheet()
    st_compact = ParagraphStyle(
        'etq_ferr_cmp',
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

    marca_txt = _caps_exibir(ferramenta.marca or '')
    desc_txt = _caps_exibir(ferramenta.descricao or '')
    cod_txt = _caps_exibir(ferramenta.codigo_numeracao or '')
    tam_s = (ferramenta.tamanho or '').strip()
    cor_s = (ferramenta.cor or '').strip()
    if tam_s and cor_s:
        rotulo_dir = 'Cor / tam.'
        valor_dir = f'{_caps_exibir(tam_s)} · {_caps_exibir(cor_s)}'
    elif cor_s:
        rotulo_dir = 'Cor'
        valor_dir = _caps_exibir(cor_s)
    elif tam_s:
        rotulo_dir = 'Tam.'
        valor_dir = _caps_exibir(tam_s)
    else:
        rotulo_dir = 'Tam.'
        valor_dir = '—'

    linha_marca = Table([[bloco_linha('Marca', marca_txt)]], colWidths=[col_txt])
    col_esq = col_txt * 0.38
    col_dir = col_txt - col_esq
    linha_inf = Table(
        [
            [
                bloco_linha('Cód. / num.', cod_txt),
                bloco_linha(rotulo_dir, valor_dir),
            ]
        ],
        colWidths=[col_esq, col_dir],
    )

    tbl_pad = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]
    linha_marca.setStyle(TableStyle(tbl_pad))
    linha_inf.setStyle(TableStyle(tbl_pad))

    linha_gap = Paragraph(
        '&nbsp;',
        ParagraphStyle(
            'etq_ferr_gap',
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
            [linha_inf],
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


def _render_ferramenta_form_modal(request, ferramenta, form):
    if ferramenta is None:
        post_url = reverse_empresa(request, 'estoque:modal_novo_ferramenta')
        titulo_modal = 'Nova ferramenta'
        excluir_url = None
    else:
        post_url = reverse_empresa(
            request, 'estoque:modal_editar_ferramenta', kwargs={'pk': ferramenta.pk}
        )
        titulo_modal = f'Editar — {ferramenta.descricao[:80]}'
        excluir_url = reverse_empresa(
            request, 'estoque:modal_excluir_ferramenta', kwargs={'pk': ferramenta.pk}
        )
    return render(
        request,
        'estoque/partials/ferramenta_form_modal.html',
        {
            'form': form,
            'post_url': post_url,
            'titulo_modal': titulo_modal,
            'ferramenta': ferramenta,
            'excluir_url': excluir_url,
        },
    )


def _modal_ferramenta_form(request, ferramenta):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:lista_ferramentas')

    if ferramenta is not None:
        ferramenta = get_object_or_404(
            Ferramenta.objects.prefetch_related('imagens'),
            pk=ferramenta.pk,
            empresa=empresa,
        )

    if request.method == 'POST':
        if ferramenta is not None:
            form = FerramentaForm(
                request.POST,
                request.FILES,
                instance=ferramenta,
                empresa=empresa,
            )
        else:
            form = FerramentaForm(
                request.POST,
                request.FILES,
                empresa=empresa,
            )
        if form.is_valid():
            saved = form.save()
            attach_auto_qrcode_to_ferramenta(saved)
            if ferramenta is None:
                registrar_auditoria(
                    request,
                    acao='create',
                    resumo=f'Ferramenta «{saved.descricao[:80]}» cadastrada.',
                    modulo='estoque',
                    detalhes={'ferramenta_id': saved.pk},
                )
                messages.success(request, 'Ferramenta cadastrada.')
            else:
                registrar_auditoria(
                    request,
                    acao='update',
                    resumo=f'Ferramenta «{saved.descricao[:80]}» atualizada.',
                    modulo='estoque',
                    detalhes={'ferramenta_id': saved.pk},
                )
                messages.success(request, 'Ferramenta atualizada.')
            return _hx_redirect_lista(request, 'estoque:lista_ferramentas')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        if ferramenta is not None:
            form = FerramentaForm(
                instance=ferramenta,
                empresa=empresa,
            )
        else:
            form = FerramentaForm(
                empresa=empresa,
            )
        preselect = (request.GET.get('preselect_categoria') or '').strip()
        if preselect.isdigit() and 'categoria' in form.fields:
            form.fields['categoria'].initial = int(preselect)

    return _render_ferramenta_form_modal(request, ferramenta, form)


@login_required
def cautela_ferramentas(request):
    """Página de cautela de ferramentas (fluxo operacional em evolução)."""
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    return render(
        request,
        'estoque/ferramentas/cautela.html',
        {
            'page_title': 'Cautela de ferramentas',
        },
    )


@login_required
def lista_ferramentas(request):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    q = (request.GET.get('q') or '').strip()
    qs = (
        Ferramenta.objects.filter(empresa=empresa, ativo=True)
        .select_related('categoria', 'fornecedor')
        .prefetch_related('imagens')
        .order_by('descricao')
    )
    if q:
        qs = qs.filter(
            Q(descricao__icontains=q)
            | Q(marca__icontains=q)
            | Q(categoria__nome__icontains=q)
            | Q(codigo_numeracao__icontains=q)
            | Q(cor__icontains=q)
        )
    ctx = {
        'page_title': 'Ferramentas',
        'ferramentas': qs,
        'q': q,
    }
    if _is_htmx(request):
        return render(request, 'estoque/ferramentas/_lista_conteudo.html', ctx)
    return render(request, 'estoque/ferramentas/lista.html', ctx)


@login_required
def modal_novo_ferramenta(request):
    return _modal_ferramenta_form(request, None)


@login_required
def modal_editar_ferramenta(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    ferramenta = get_object_or_404(Ferramenta, pk=pk, empresa=empresa)
    return _modal_ferramenta_form(request, ferramenta)


@login_required
def modal_gerar_qrcode_ferramenta(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    ferramenta = get_object_or_404(
        Ferramenta.objects.prefetch_related('imagens'),
        pk=pk,
        empresa=empresa,
    )

    if request.method != 'POST':
        return redirect_empresa(request, 'estoque:detalhes_ferramenta', pk=pk)

    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:detalhes_ferramenta', pk=pk)

    if ferramenta.qrcode_imagem:
        messages.info(request, 'Esta ferramenta já possui QR Code.')
    else:
        from django.conf import settings

        ok, err = attach_auto_qrcode_to_ferramenta(ferramenta)
        ferramenta.refresh_from_db()
        if ok and ferramenta.qrcode_imagem:
            messages.success(request, 'QR Code gerado.')
        else:
            msg = 'Não foi possível gerar o QR Code. Tente de novo.'
            if settings.DEBUG and err:
                msg = f'{msg} ({err})'
            messages.warning(request, msg)

    ferramenta.refresh_from_db()
    return render(
        request,
        'estoque/ferramentas/_detalhes_qrcode_card.html',
        {'ferramenta': ferramenta},
    )


@login_required
def modal_excluir_qrcode_ferramenta(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    ferramenta = get_object_or_404(
        Ferramenta.objects.prefetch_related('imagens'),
        pk=pk,
        empresa=empresa,
    )

    if request.method != 'POST':
        return redirect_empresa(request, 'estoque:detalhes_ferramenta', pk=pk)

    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:detalhes_ferramenta', pk=pk)

    if ferramenta.qrcode_imagem:
        ferramenta.qrcode_imagem.delete(save=False)
        ferramenta.save(update_fields=['qrcode_imagem'])
        messages.success(
            request,
            'QR Code removido. Use «Gerar QR Code» para criar outro.',
        )
    else:
        messages.info(request, 'Esta ferramenta não tinha QR Code.')

    ferramenta.refresh_from_db()
    return render(
        request,
        'estoque/ferramentas/_detalhes_qrcode_card.html',
        {'ferramenta': ferramenta},
    )


@login_required
def modal_excluir_ferramenta(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    ferramenta = get_object_or_404(Ferramenta, pk=pk, empresa=empresa)
    if not _is_htmx(request):
        return redirect_empresa(
            request, 'estoque:ferramenta_excluir', kwargs={'pk': pk}
        )

    if ferramenta_precisa_arquivar(ferramenta):
        resp = HttpResponse(status=200)
        resp['HX-Redirect'] = reverse_empresa(
            request, 'estoque:ferramenta_excluir', kwargs={'pk': pk}
        )
        return resp

    return render(
        request,
        'estoque/partials/ferramenta_excluir_modal.html',
        {
            'ferramenta': ferramenta,
            'excluir_url': reverse_empresa(
                request, 'estoque:ferramenta_excluir', kwargs={'pk': pk}
            ),
            'voltar_editar_url': reverse_empresa(
                request, 'estoque:modal_editar_ferramenta', kwargs={'pk': pk}
            ),
        },
    )


@login_required
def ferramenta_novo(request):
    return redirect_empresa(request, 'estoque:lista_ferramentas')


@login_required
def detalhes_ferramenta(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    ferramenta = get_object_or_404(
        Ferramenta.objects.select_related('categoria', 'fornecedor').prefetch_related(
            'imagens'
        ),
        pk=pk,
        empresa=empresa,
    )

    cautela_em_uso = (
        Cautela.objects.filter(
            empresa=empresa,
            situacao=Cautela.Situacao.ATIVA,
            ferramentas=ferramenta,
        )
        .select_related('funcionario')
        .order_by('-data_inicio_cautela', '-pk')
        .first()
    )

    entregas_hist = (
        Entrega_Cautela.objects.filter(
            ferramentas_devolvidas=ferramenta,
            cautela__empresa=empresa,
        )
        .select_related(
            'cautela',
            'cautela__funcionario',
            'motivo',
            'situacao_ferramentas',
        )
        .order_by('-data_entrega', '-pk')[:30]
    )
    historico_devolucoes = []
    for ent in entregas_hist:
        ini = ent.cautela.data_inicio_cautela
        fim = ent.data_entrega
        if fim >= ini:
            dias_periodo = (fim - ini).days + 1
        else:
            dias_periodo = None
        historico_devolucoes.append(
            {
                'entrega': ent,
                'dias_periodo': dias_periodo,
            }
        )

    return render(
        request,
        'estoque/ferramentas/detalhes.html',
        {
            'page_title': ferramenta.descricao[:120],
            'ferramenta': ferramenta,
            'cautela_em_uso': cautela_em_uso,
            'historico_devolucoes': historico_devolucoes,
        },
    )


@login_required
def ferramenta_editar(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    get_object_or_404(Ferramenta, pk=pk, empresa=empresa)
    return redirect_empresa(request, 'estoque:detalhes_ferramenta', pk=pk)


@login_required
def ferramenta_imagem_excluir(request, ferramenta_pk, imagem_pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    ferramenta = get_object_or_404(Ferramenta, pk=ferramenta_pk, empresa=empresa)
    img = get_object_or_404(FerramentaImagem, pk=imagem_pk, ferramenta=ferramenta)
    if request.method == 'POST':
        img.imagem.delete(save=False)
        img.delete()
        messages.success(request, 'Imagem removida.')
        _garantir_uma_imagem_padrao_ferramenta(ferramenta)
        ferramenta = _ferramenta_com_imagens_prefetch(ferramenta, empresa)
        if _is_htmx(request):
            return render(
                request,
                'estoque/ferramentas/_detalhes_imagens_card.html',
                {'ferramenta': ferramenta},
            )
        return redirect_empresa(request, 'estoque:detalhes_ferramenta', pk=ferramenta.pk)

    return redirect_empresa(request, 'estoque:detalhes_ferramenta', pk=ferramenta.pk)


@login_required
def modal_adicionar_imagens_ferramenta(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    ferramenta = get_object_or_404(Ferramenta, pk=pk, empresa=empresa)
    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:detalhes_ferramenta', pk=pk)
    if request.method == 'POST':
        files = request.FILES.getlist('imagens')
        if not files:
            messages.error(request, 'Selecione ao menos uma imagem.')
            response = render(
                request,
                'estoque/ferramentas/modal_adicionar_imagens.html',
                {'ferramenta': ferramenta},
            )
            response['HX-Retarget'] = '#modal-content'
            response['HX-Reswap'] = 'innerHTML'
            return response
        _anexar_imagens_novas(ferramenta, files)
        messages.success(request, 'Imagens adicionadas.')
        ferramenta = _ferramenta_com_imagens_prefetch(ferramenta, empresa)
        return render(
            request,
            'estoque/ferramentas/_detalhes_imagens_card.html',
            {'ferramenta': ferramenta},
        )
    return render(
        request,
        'estoque/ferramentas/modal_adicionar_imagens.html',
        {'ferramenta': ferramenta},
    )


@login_required
def ferramenta_imagem_definir_padrao(request, ferramenta_pk, imagem_pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    ferramenta = get_object_or_404(Ferramenta, pk=ferramenta_pk, empresa=empresa)
    imagem = get_object_or_404(
        FerramentaImagem, pk=imagem_pk, ferramenta=ferramenta
    )
    if request.method != 'POST':
        return redirect_empresa(request, 'estoque:detalhes_ferramenta', pk=ferramenta.pk)
    with transaction.atomic():
        FerramentaImagem.objects.filter(ferramenta=ferramenta).update(padrao=False)
        imagem.padrao = True
        imagem.save(update_fields=['padrao'])
    messages.success(request, 'Imagem padrão para visualização atualizada.')
    ferramenta = _ferramenta_com_imagens_prefetch(ferramenta, empresa)
    if _is_htmx(request):
        return render(
            request,
            'estoque/ferramentas/_detalhes_imagens_card.html',
            {'ferramenta': ferramenta},
        )
    return redirect_empresa(request, 'estoque:detalhes_ferramenta', pk=ferramenta.pk)


@login_required
def imprimir_etiqueta_ferramenta(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    ferramenta = get_object_or_404(Ferramenta, pk=pk, empresa=empresa)
    data = _etiqueta_ferramenta_pdf_bytes(ferramenta)
    resp = HttpResponse(data, content_type='application/pdf')
    resp['Content-Disposition'] = (
        f'inline; filename="etiqueta_ferramenta_{ferramenta.pk}.pdf"'
    )
    return resp


@login_required
def imprimir_etiqueta_ferramenta_png(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')
    ferramenta = get_object_or_404(Ferramenta, pk=pk, empresa=empresa)
    try:
        pdf_bytes = _etiqueta_ferramenta_pdf_bytes(ferramenta)
        png_bytes = _etiqueta_pdf_para_png_bytes(pdf_bytes)
    except ImportError:
        messages.error(
            request,
            'Exportação em PNG não está disponível (dependência PyMuPDF ausente).',
        )
        return redirect_empresa(
            request, 'estoque:detalhes_ferramenta', kwargs={'pk': pk}
        )
    resp = HttpResponse(png_bytes, content_type='image/png')
    resp['Content-Disposition'] = (
        f'inline; filename="etiqueta_ferramenta_{ferramenta.pk}.png"'
    )
    return resp


@login_required
def ferramenta_excluir(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    ferramenta = get_object_or_404(Ferramenta, pk=pk, empresa=empresa)
    cautelas_v = list(cautelas_com_ferramenta(ferramenta))
    tem_vinculos = bool(cautelas_v)

    if request.method == 'POST':
        if tem_vinculos:
            if request.POST.get('confirmar_arquivamento') != '1':
                messages.error(
                    request,
                    'Marque a confirmação para arquivar esta ferramenta com vínculos.',
                )
            else:
                with transaction.atomic():
                    locked = Ferramenta.objects.select_for_update().get(
                        pk=ferramenta.pk, empresa=empresa
                    )
                    desc_antes = locked.descricao[:120]
                    nova = descricao_com_sufixo_excluido(
                        locked.descricao,
                        Ferramenta._meta.get_field('descricao').max_length,
                    )
                    locked.descricao = nova
                    locked.ativo = False
                    locked.save(update_fields=['descricao', 'ativo'])
                registrar_auditoria(
                    request,
                    acao='update',
                    resumo=(
                        'Ferramenta arquivada (excluída lógica): '
                        f'«{desc_antes}» → «{nova[:120]}».'
                    ),
                    modulo='estoque',
                    detalhes={'ferramenta_id': locked.pk, 'arquivado': True},
                )
                messages.success(
                    request,
                    'Ferramenta arquivada: o nome passou a incluir «(EXCLUÍDO)» e o '
                    'cadastro ficou inativo, preservando o histórico em cautelas.',
                )
                if _is_htmx(request):
                    return _hx_redirect_lista(request, 'estoque:lista_ferramentas')
                return redirect_empresa(request, 'estoque:lista_ferramentas')
        else:
            desc = ferramenta.descricao[:120]
            fid = ferramenta.pk
            for img in list(ferramenta.imagens.all()):
                img.imagem.delete(save=False)
                img.delete()
            if ferramenta.qrcode_imagem:
                ferramenta.qrcode_imagem.delete(save=False)
            ferramenta.delete()
            registrar_auditoria(
                request,
                acao='delete',
                resumo=f'Ferramenta «{desc}» excluída.',
                modulo='estoque',
                detalhes={'ferramenta_id': fid},
            )
            messages.success(request, 'Ferramenta excluída.')
            if _is_htmx(request):
                return _hx_redirect_lista(request, 'estoque:lista_ferramentas')
            return redirect_empresa(request, 'estoque:lista_ferramentas')

    nova_desc_prev = descricao_com_sufixo_excluido(
        ferramenta.descricao,
        Ferramenta._meta.get_field('descricao').max_length,
    )
    return render(
        request,
        'estoque/ferramentas/excluir.html',
        {
            'page_title': 'Excluir ferramenta',
            'ferramenta': ferramenta,
            'tem_vinculos': tem_vinculos,
            'cautelas_vinculadas': cautelas_v,
            'nova_descricao_prevista': nova_desc_prev,
        },
    )
