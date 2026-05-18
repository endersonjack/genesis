from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from core.urlutils import reverse_empresa

from ..forms import CurriculoForm
from ..models import Cargo, Curriculo, CurriculoAnexo
from .base import _empresa_ativa_or_redirect


def _hx_redirect_banco_curriculos(request, return_q: str = '') -> HttpResponse:
    path = reverse_empresa(request, 'rh:banco_curriculos')
    q = (return_q or '').strip()
    if q:
        path = f'{path}?{q}'
    response = HttpResponse(status=204)
    response['HX-Redirect'] = path
    return response


def banco_curriculos(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para visualizar o banco de currículos.',
    )
    if redirect_response:
        return redirect_response

    curriculos = (
        Curriculo.objects.filter(empresa=empresa_ativa)
        .select_related('funcao')
        .prefetch_related('anexos')
    )

    q = request.GET.get('q', '').strip()
    funcao_id = request.GET.get('funcao', '').strip()
    status = request.GET.get('status', '').strip()

    if q:
        curriculos = curriculos.filter(
            Q(nome__icontains=q)
            | Q(telefone__icontains=q)
            | Q(email__icontains=q)
            | Q(indicacao__icontains=q)
            | Q(endereco__icontains=q)
        )

    if funcao_id:
        curriculos = curriculos.filter(funcao_id=funcao_id)

    if status:
        curriculos = curriculos.filter(status=status)

    cargos = Cargo.objects.filter(empresa=empresa_ativa).order_by('nome')
    total_curriculos = Curriculo.objects.filter(empresa=empresa_ativa).count()
    contagem_por_funcao = (
        Cargo.objects.filter(empresa=empresa_ativa, curriculos__isnull=False)
        .annotate(total_curriculos=Count('curriculos', filter=Q(curriculos__empresa=empresa_ativa)))
        .filter(total_curriculos__gt=0)
        .order_by('nome')
    )

    context = {
        'curriculos': curriculos.order_by('-data', 'nome'),
        'cargos': cargos,
        'status_choices': Curriculo.STATUS_CHOICES,
        'total_curriculos': total_curriculos,
        'contagem_por_funcao': contagem_por_funcao,
        'total_resultados': curriculos.count(),
        'filtros_ativos': any([q, funcao_id, status]),
    }
    return render(request, 'rh/curriculos/banco.html', context)


def adicionar_curriculo(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de cadastrar currículos.',
    )
    if redirect_response:
        return redirect_response

    if request.method == 'POST':
        form = CurriculoForm(
            request.POST,
            request.FILES,
            empresa_ativa=empresa_ativa,
        )
        return_q = (request.POST.get('return_q') or '').strip()
        if form.is_valid():
            curriculo = form.save(commit=False)
            curriculo.empresa = empresa_ativa
            curriculo.save()

            for arquivo in request.FILES.getlist('anexos'):
                CurriculoAnexo.objects.create(
                    curriculo=curriculo,
                    arquivo=arquivo,
                    descricao=arquivo.name,
                )

            messages.success(request, 'Currículo adicionado ao banco.')
            return _hx_redirect_banco_curriculos(request, return_q=return_q)
    else:
        form = CurriculoForm(empresa_ativa=empresa_ativa)
        return_q = (request.GET.get('return_q') or '').strip()

    return render(
        request,
        'rh/curriculos/modals/modal_curriculo_form.html',
        {
            'form': form,
            'titulo': 'Adicionar Currículo',
            'subtitulo': 'Registre os dados do candidato e anexe o currículo recebido.',
            'modo': 'criar',
            'curriculo': None,
            'return_q': return_q,
        },
    )


def editar_curriculo(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de editar currículos.',
    )
    if redirect_response:
        return redirect_response

    curriculo = get_object_or_404(Curriculo, pk=pk, empresa=empresa_ativa)

    if request.method == 'POST':
        form = CurriculoForm(
            request.POST,
            request.FILES,
            instance=curriculo,
            empresa_ativa=empresa_ativa,
        )
        return_q = (request.POST.get('return_q') or '').strip()
        if form.is_valid():
            curriculo = form.save()

            for arquivo in request.FILES.getlist('anexos'):
                CurriculoAnexo.objects.create(
                    curriculo=curriculo,
                    arquivo=arquivo,
                    descricao=arquivo.name,
                )

            messages.success(request, 'Currículo atualizado com sucesso.')
            return _hx_redirect_banco_curriculos(request, return_q=return_q)
    else:
        form = CurriculoForm(instance=curriculo, empresa_ativa=empresa_ativa)
        return_q = (request.GET.get('return_q') or '').strip()

    return render(
        request,
        'rh/curriculos/modals/modal_curriculo_form.html',
        {
            'form': form,
            'titulo': 'Editar Currículo',
            'subtitulo': 'Atualize os dados do candidato e adicione novos anexos quando necessário.',
            'modo': 'editar',
            'curriculo': curriculo,
            'return_q': return_q,
        },
    )


def excluir_curriculo(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de excluir currículos.',
    )
    if redirect_response:
        return redirect_response

    curriculo = get_object_or_404(Curriculo, pk=pk, empresa=empresa_ativa)

    if request.method == 'POST':
        return_q = (request.POST.get('return_q') or '').strip()
        nome = curriculo.nome
        curriculo.delete()
        messages.success(request, f'Currículo de {nome} excluído com sucesso.')
        return _hx_redirect_banco_curriculos(request, return_q=return_q)

    return render(
        request,
        'rh/curriculos/modals/modal_curriculo_excluir.html',
        {
            'curriculo': curriculo,
            'return_q': (request.GET.get('return_q') or '').strip(),
        },
    )
