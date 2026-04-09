from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.registry import registrar_auditoria

from core.urlutils import redirect_empresa, reverse_empresa

from .forms import LocalForm
from .models import Local, LocalTrabalhoAtivo


def _is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def _negar_mutacao_local_para_apontador(request):
    """
    Apontador «puro» só consulta o cadastro de locais; não cria, edita nem exclui.
    """
    if getattr(request, 'usuario_so_apontador', False):
        messages.warning(
            request,
            'Como apontador, você só pode visualizar os locais cadastrados.',
        )
        return redirect_empresa(request, 'local:lista')
    return None


def _redirect_lista_htmx(request):
    response = HttpResponse(status=200)
    response['HX-Redirect'] = reverse_empresa(request, 'local:lista')
    return response


@login_required
def lista_locais(request):
    empresa = getattr(request, 'empresa_ativa', None)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa para gerenciar os locais.')
        return redirect('selecionar_empresa')

    locais = Local.objects.filter(empresa=empresa).order_by('nome')
    return render(
        request,
        'local/lista.html',
        {
            'page_title': 'Locais',
            'locais': locais,
        },
    )

@login_required
def local_detalhe(request, pk):
    empresa = getattr(request, 'empresa_ativa', None)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa para visualizar o local.')
        return redirect('selecionar_empresa')

    local = get_object_or_404(Local, pk=pk, empresa=empresa)
    ativo_em_trabalho = LocalTrabalhoAtivo.objects.filter(empresa=empresa, local=local).exists()
    return render(
        request,
        'local/detalhe.html',
        {
            'page_title': f'Local — {local.nome}',
            'local': local,
            'ativo_em_trabalho': ativo_em_trabalho,
        },
    )


@login_required
def local_criar(request):
    empresa = getattr(request, 'empresa_ativa', None)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    denied = _negar_mutacao_local_para_apontador(request)
    if denied:
        return denied

    form = LocalForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa
            obj.save()
            registrar_auditoria(
                request,
                acao='create',
                resumo=f'Local "{obj.nome}" cadastrado.',
                modulo='local',
                detalhes={'local_id': obj.pk},
            )
            messages.success(request, f'Local "{obj.nome}" cadastrado com sucesso.')
            if _is_htmx(request):
                return _redirect_lista_htmx(request)
            return redirect_empresa(request, 'local:lista')
        messages.error(request, 'Revise os campos do formulário.')

    return render(
        request,
        'local/_form_modal.html',
        {
            'form': form,
            'modo': 'criar',
            'local': None,
        },
    )


@login_required
def local_criar_page(request):
    empresa = getattr(request, 'empresa_ativa', None)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    denied = _negar_mutacao_local_para_apontador(request)
    if denied:
        return denied

    form = LocalForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa
            obj.save()
            registrar_auditoria(
                request,
                acao='create',
                resumo=f'Local "{obj.nome}" cadastrado.',
                modulo='local',
                detalhes={'local_id': obj.pk},
            )
            messages.success(request, f'Local "{obj.nome}" cadastrado com sucesso.')
            return redirect_empresa(request, 'local:detalhe', pk=obj.pk)
        messages.error(request, 'Revise os campos do formulário.')

    return render(
        request,
        'local/form_page.html',
        {'page_title': 'Novo local', 'form': form, 'modo': 'criar', 'local': None},
    )


@login_required
def local_editar(request, pk):
    empresa = getattr(request, 'empresa_ativa', None)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    denied = _negar_mutacao_local_para_apontador(request)
    if denied:
        return denied

    local = get_object_or_404(Local, pk=pk, empresa=empresa)
    form = LocalForm(request.POST or None, instance=local)

    if request.method == 'POST':
        if form.is_valid():
            salvo = form.save()
            registrar_auditoria(
                request,
                acao='update',
                resumo=f'Local "{salvo.nome}" atualizado.',
                modulo='local',
                detalhes={'local_id': salvo.pk},
            )
            messages.success(request, f'Local "{salvo.nome}" atualizado com sucesso.')
            if _is_htmx(request):
                return _redirect_lista_htmx(request)
            return redirect_empresa(request, 'local:lista')
        messages.error(request, 'Revise os campos do formulário.')

    return render(
        request,
        'local/_form_modal.html',
        {
            'form': form,
            'modo': 'editar',
            'local': local,
        },
    )


@login_required
def local_editar_page(request, pk):
    empresa = getattr(request, 'empresa_ativa', None)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    denied = _negar_mutacao_local_para_apontador(request)
    if denied:
        return denied

    local = get_object_or_404(Local, pk=pk, empresa=empresa)
    form = LocalForm(request.POST or None, instance=local)
    ativo_em_trabalho = LocalTrabalhoAtivo.objects.filter(empresa=empresa, local=local).exists()

    if request.method == 'POST':
        if form.is_valid():
            salvo = form.save()
            quer_ativo = request.POST.get('ativar_como_local_trabalho') in ('1', 'true', 'on', 'yes')
            if quer_ativo and not ativo_em_trabalho:
                # Tenta preencher coordenadas ao ativar, se possível.
                if (salvo.latitude is None or salvo.longitude is None):
                    src = (salvo.link_maps_embed or '').strip()
                    lat, lng = Local.parse_lat_lng_from_maps(src)
                    if lat is not None and lng is not None:
                        salvo.latitude = lat
                        salvo.longitude = lng
                        salvo.save(update_fields=['latitude', 'longitude'])
                LocalTrabalhoAtivo.objects.create(empresa=empresa, local=salvo)
            elif (not quer_ativo) and ativo_em_trabalho:
                LocalTrabalhoAtivo.objects.filter(empresa=empresa, local=salvo).delete()
            registrar_auditoria(
                request,
                acao='update',
                resumo=f'Local "{salvo.nome}" atualizado.',
                modulo='local',
                detalhes={'local_id': salvo.pk},
            )
            messages.success(request, f'Local "{salvo.nome}" atualizado com sucesso.')
            return redirect_empresa(request, 'local:detalhe', pk=salvo.pk)
        messages.error(request, 'Revise os campos do formulário.')

    return render(
        request,
        'local/form_page.html',
        {
            'page_title': f'Editar local — {local.nome}',
            'form': form,
            'modo': 'editar',
            'local': local,
            'ativo_em_trabalho': ativo_em_trabalho,
        },
    )


@login_required
def local_excluir(request, pk):
    empresa = getattr(request, 'empresa_ativa', None)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    denied = _negar_mutacao_local_para_apontador(request)
    if denied:
        return denied

    local = get_object_or_404(Local, pk=pk, empresa=empresa)

    if request.method == 'POST':
        nome = local.nome
        local_id = local.pk
        local.delete()
        registrar_auditoria(
            request,
            acao='delete',
            resumo=f'Local "{nome}" excluído.',
            modulo='local',
            detalhes={'local_id': local_id},
        )
        messages.success(request, f'Local "{nome}" excluído com sucesso.')
        if _is_htmx(request):
            return _redirect_lista_htmx(request)
        return redirect_empresa(request, 'local:lista')

    return render(
        request,
        'local/_excluir_modal.html',
        {'local': local},
    )


@login_required
def local_excluir_page(request, pk):
    empresa = getattr(request, 'empresa_ativa', None)
    if not empresa:
        messages.error(request, 'Selecione uma empresa ativa.')
        return redirect('selecionar_empresa')

    denied = _negar_mutacao_local_para_apontador(request)
    if denied:
        return denied

    local = get_object_or_404(Local, pk=pk, empresa=empresa)

    if request.method == 'POST':
        nome = local.nome
        local_id = local.pk
        local.delete()
        registrar_auditoria(
            request,
            acao='delete',
            resumo=f'Local "{nome}" excluído.',
            modulo='local',
            detalhes={'local_id': local_id},
        )
        messages.success(request, f'Local "{nome}" excluído com sucesso.')
        return redirect_empresa(request, 'local:lista')

    return render(
        request,
        'local/excluir_page.html',
        {'page_title': f'Excluir local — {local.nome}', 'local': local},
    )
