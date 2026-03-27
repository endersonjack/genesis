from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from controles_rh.models import Competencia, ValeTransporteItem, ValeTransporteTabela
from rh.models import Funcionario
from controles_rh.forms import ValeTransporteTabelaForm, ValeTransporteItemForm


def _is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def _get_empresa_ativa(request):
    return getattr(request, 'empresa_ativa', None)


def _get_competencia_empresa(request, competencia_pk):
    empresa_ativa = _get_empresa_ativa(request)

    queryset = Competencia.objects.select_related('empresa')

    if empresa_ativa:
        queryset = queryset.filter(empresa=empresa_ativa)
    else:
        queryset = queryset.none()

    return get_object_or_404(queryset, pk=competencia_pk)


def _get_tabela_vt_empresa(request, pk):
    empresa_ativa = _get_empresa_ativa(request)

    queryset = ValeTransporteTabela.objects.select_related(
        'competencia',
        'competencia__empresa'
    )

    if empresa_ativa:
        queryset = queryset.filter(competencia__empresa=empresa_ativa)
    else:
        queryset = queryset.none()

    return get_object_or_404(queryset, pk=pk)


def _get_funcionarios_para_vt(competencia):
    """
    Retorna os funcionários admitidos da empresa da competência.
    Ajuste o filtro de situação conforme o padrão real do model Funcionario.
    """
    funcionarios = Funcionario.objects.filter(
    empresa=competencia.empresa
).exclude(
    situacao_atual__in=['demitido', 'inativo']
).select_related('cargo').order_by('nome')

    return funcionarios


def _criar_itens_iniciais_vt(tabela):
    """
    Gera automaticamente os itens da tabela VT com base nos funcionários
    admitidos da empresa da competência.
    """
    funcionarios = _get_funcionarios_para_vt(tabela.competencia)

    itens = []
    for ordem, funcionario in enumerate(funcionarios or [], start=1):
        cargo = getattr(funcionario, 'cargo', None)
        banco = getattr(funcionario, 'banco', None)

        itens.append(
            ValeTransporteItem(
                tabela=tabela,
                funcionario=funcionario,
                nome=getattr(funcionario, 'nome', '') or '',
                funcao=str(cargo) if cargo else '',
                endereco=getattr(funcionario, 'endereco_completo', '') or '',
                valor_pagar=getattr(funcionario, 'valor_vale_transporte', 0) or 0,
                pix=getattr(funcionario, 'pix', '') or '',
                tipo_pix=getattr(funcionario, 'tipo_pix', '') or '',
                banco=str(banco) if banco else '',
                ordem=ordem,
            )
        )

    if itens:
        ValeTransporteItem.objects.bulk_create(itens)


@login_required
def criar_tabela_vt(request, competencia_pk):
    """
    Cria uma nova tabela de VT dentro da competência e gera os itens iniciais.
    """
    competencia = _get_competencia_empresa(request, competencia_pk)

    form = ValeTransporteTabelaForm(
        request.POST or None,
        competencia=competencia
    )

    if request.method == 'POST':
        if form.is_valid():
            with transaction.atomic():
                tabela = form.save()
                _criar_itens_iniciais_vt(tabela)

            messages.success(request, f'Tabela "{tabela.nome}" criada com sucesso.')

            if _is_htmx(request):
                response = HttpResponse(status=204)
                response['HX-Refresh'] = 'true'
                return response

            return redirect('controles_rh:detalhe_tabela_vt', pk=tabela.pk)

        messages.error(request, 'Não foi possível criar a tabela de VT. Revise os campos.')

    context = {
        'competencia': competencia,
        'tabela': None,
        'form': form,
        'modo': 'criar',
    }
    return render(request, 'controles_rh/vale_transporte/_form_tabela_modal.html', context)


@login_required
def detalhe_tabela_vt(request, pk):
    """
    Exibe os detalhes da tabela VT e seus itens.
    """
    tabela = _get_tabela_vt_empresa(request, pk)

    itens = tabela.itens.select_related('funcionario').order_by('ordem', 'nome', 'id')

    context = {
        'page_title': f'VT - {tabela.nome}',
        'tabela': tabela,
        'competencia': tabela.competencia,
        'itens': itens,
        'total_itens': itens.count(),
        'total_valor': tabela.total_valor,
    }
    return render(request, 'controles_rh/vale_transporte/detalhe_tabela.html', context)


@login_required
def editar_tabela_vt(request, pk):
    """
    Edita os dados da tabela de VT.
    """
    tabela = _get_tabela_vt_empresa(request, pk)

    form = ValeTransporteTabelaForm(
        request.POST or None,
        instance=tabela,
        competencia=tabela.competencia
    )

    if request.method == 'POST':
        if form.is_valid():
            tabela = form.save()
            messages.success(request, f'Tabela "{tabela.nome}" atualizada com sucesso.')

            if _is_htmx(request):
                response = HttpResponse(status=204)
                response['HX-Refresh'] = 'true'
                return response

            return redirect('controles_rh:detalhe_tabela_vt', pk=tabela.pk)

        messages.error(request, 'Não foi possível atualizar a tabela de VT.')

    context = {
        'competencia': tabela.competencia,
        'tabela': tabela,
        'form': form,
        'modo': 'editar',
    }
    return render(request, 'controles_rh/vale_transporte/_form_tabela_modal.html', context)


@login_required
def excluir_tabela_vt(request, pk):
    """
    Exclui a tabela de VT.
    """
    tabela = _get_tabela_vt_empresa(request, pk)

    if request.method == 'POST':
        competencia_pk = tabela.competencia.pk
        nome = tabela.nome
        tabela.delete()

        messages.success(request, f'Tabela "{nome}" excluída com sucesso.')

        if _is_htmx(request):
            response = HttpResponse(status=204)
            response['HX-Refresh'] = 'true'
            return response

        return redirect('controles_rh:detalhe_competencia', pk=competencia_pk)

    context = {
        'tabela': tabela,
        'competencia': tabela.competencia,
    }
    return render(request, 'controles_rh/vale_transporte/_excluir_tabela_modal.html', context)

def _get_item_vt_empresa(request, pk):
    empresa_ativa = _get_empresa_ativa(request)

    queryset = ValeTransporteItem.objects.select_related(
        'tabela',
        'tabela__competencia',
        'tabela__competencia__empresa',
        'funcionario',
    )

    if empresa_ativa:
        queryset = queryset.filter(tabela__competencia__empresa=empresa_ativa)
    else:
        queryset = queryset.none()

    return get_object_or_404(queryset, pk=pk)


@login_required
def adicionar_item_vt(request, tabela_pk):
    """
    Adiciona uma nova linha manual à tabela VT.
    """
    tabela = _get_tabela_vt_empresa(request, tabela_pk)

    ultima_ordem = tabela.itens.order_by('-ordem').values_list('ordem', flat=True).first() or 0

    form = ValeTransporteItemForm(
        request.POST or None,
        tabela=tabela,
        initial={'ordem': ultima_ordem + 1, 'ativo': True}
    )

    if request.method == 'POST':
        if form.is_valid():
            item = form.save()
            messages.success(request, f'Linha "{item.nome_exibicao}" adicionada com sucesso.')

            if _is_htmx(request):
                response = HttpResponse(status=204)
                response['HX-Refresh'] = 'true'
                return response

            return redirect('controles_rh:detalhe_tabela_vt', pk=tabela.pk)

        messages.error(request, 'Não foi possível adicionar a linha.')

    context = {
        'tabela': tabela,
        'competencia': tabela.competencia,
        'item': None,
        'form': form,
        'modo': 'criar',
    }
    return render(request, 'controles_rh/vale_transporte/_form_item_modal.html', context)


@login_required
def editar_item_vt(request, pk):
    """
    Edita uma linha da tabela VT.
    """
    item = _get_item_vt_empresa(request, pk)
    tabela = item.tabela

    form = ValeTransporteItemForm(
        request.POST or None,
        instance=item,
        tabela=tabela
    )

    if request.method == 'POST':
        if form.is_valid():
            item = form.save()
            messages.success(request, f'Linha "{item.nome_exibicao}" atualizada com sucesso.')

            if _is_htmx(request):
                response = HttpResponse(status=204)
                response['HX-Refresh'] = 'true'
                return response

            return redirect('controles_rh:detalhe_tabela_vt', pk=tabela.pk)

        messages.error(request, 'Não foi possível atualizar a linha.')

    context = {
        'tabela': tabela,
        'competencia': tabela.competencia,
        'item': item,
        'form': form,
        'modo': 'editar',
    }
    return render(request, 'controles_rh/vale_transporte/_form_item_modal.html', context)


@login_required
def excluir_item_vt(request, pk):
    """
    Exclui uma linha da tabela VT.
    """
    item = _get_item_vt_empresa(request, pk)
    tabela = item.tabela

    if request.method == 'POST':
        nome = item.nome_exibicao
        tabela_pk = tabela.pk
        item.delete()

        messages.success(request, f'Linha "{nome}" excluída com sucesso.')

        if _is_htmx(request):
            response = HttpResponse(status=204)
            response['HX-Refresh'] = 'true'
            return response

        return redirect('controles_rh:detalhe_tabela_vt', pk=tabela_pk)

    context = {
        'item': item,
        'tabela': tabela,
        'competencia': tabela.competencia,
    }
    return render(request, 'controles_rh/vale_transporte/_excluir_item_modal.html', context)