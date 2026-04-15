from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.registry import registrar_auditoria

from core.urlutils import redirect_empresa, reverse_empresa

from .forms import FerramentaForm
from .models import Ferramenta, FerramentaImagem
from .qr_item import attach_auto_qrcode_to_ferramenta


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
    for i, f in enumerate(files_list):
        FerramentaImagem.objects.create(ferramenta=ferramenta, imagem=f, ordem=nxt + i)


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
                lock_qrcode_imagem=True,
            )
        else:
            form = FerramentaForm(
                request.POST,
                request.FILES,
                empresa=empresa,
                lock_qrcode_imagem=True,
            )
        if form.is_valid():
            saved = form.save()
            _anexar_imagens_novas(saved, request.FILES.getlist('imagens'))
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
                lock_qrcode_imagem=True,
            )
        else:
            form = FerramentaForm(
                empresa=empresa,
                lock_qrcode_imagem=True,
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
        Ferramenta.objects.filter(empresa=empresa)
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
        return redirect_empresa(request, 'estoque:lista_ferramentas')

    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:lista_ferramentas')

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

    form = FerramentaForm(
        instance=ferramenta,
        empresa=empresa,
        lock_qrcode_imagem=True,
    )
    return _render_ferramenta_form_modal(request, ferramenta, form)


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
        return redirect_empresa(request, 'estoque:lista_ferramentas')

    if not _is_htmx(request):
        return redirect_empresa(request, 'estoque:lista_ferramentas')

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
    form = FerramentaForm(
        instance=ferramenta,
        empresa=empresa,
        lock_qrcode_imagem=True,
    )
    return _render_ferramenta_form_modal(request, ferramenta, form)


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
    return render(
        request,
        'estoque/ferramentas/detalhes.html',
        {
            'page_title': ferramenta.descricao[:120],
            'ferramenta': ferramenta,
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
        ferramenta = get_object_or_404(
            Ferramenta.objects.prefetch_related('imagens'),
            pk=ferramenta_pk,
            empresa=empresa,
        )
        form = FerramentaForm(
            instance=ferramenta,
            empresa=empresa,
            lock_qrcode_imagem=True,
        )
        if _is_htmx(request):
            return _render_ferramenta_form_modal(request, ferramenta, form)
        return redirect_empresa(request, 'estoque:detalhes_ferramenta', pk=ferramenta.pk)

    return redirect_empresa(request, 'estoque:detalhes_ferramenta', pk=ferramenta.pk)


@login_required
def ferramenta_excluir(request, pk):
    empresa = _empresa(request)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    ferramenta = get_object_or_404(Ferramenta, pk=pk, empresa=empresa)
    if request.method == 'POST':
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

    return render(
        request,
        'estoque/ferramentas/excluir.html',
        {
            'page_title': 'Excluir ferramenta',
            'ferramenta': ferramenta,
        },
    )
