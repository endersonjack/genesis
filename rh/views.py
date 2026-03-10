from datetime import date

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    FuncionarioForm,
    DependenteFormSet,
    CargoForm,
    LotacaoForm,
)
from .models import (
    Funcionario,
    Cargo,
    Lotacao,
)


def dashboard_rh(request):
    empresa_ativa = getattr(request, 'empresa_ativa', None)

    if not empresa_ativa:
        messages.warning(request, 'Selecione uma empresa para visualizar o RH.')
        return redirect('selecionar_empresa')

    funcionarios = Funcionario.objects.filter(empresa=empresa_ativa).select_related(
        'cargo',
        'lotacao',
        'tipo_contrato',
    )

    hoje = date.today()
    mes_atual = hoje.month

    total_funcionarios = funcionarios.count()
    total_ativos = funcionarios.filter(situacao_atual='ativo').count()
    total_admitidos = funcionarios.filter(situacao_atual='admitido').count()
    total_afastados = funcionarios.filter(situacao_atual='afastado').count()
    total_ferias = funcionarios.filter(situacao_atual='ferias').count()
    total_demitidos = funcionarios.filter(situacao_atual='demitido').count()

    admitidos_recentes = funcionarios.filter(
        data_admissao__isnull=False
    ).order_by('-data_admissao')[:8]

    aniversariantes_mes = funcionarios.filter(
        data_nascimento__month=mes_atual
    ).order_by('data_nascimento__day', 'nome')[:10]

    cargos_resumo = (
        funcionarios.values('cargo__id', 'cargo__nome')
        .annotate(total=Count('id'))
        .order_by('-total', 'cargo__nome')
    )

    lotacoes_resumo = (
        funcionarios.values('lotacao__id', 'lotacao__nome')
        .annotate(total=Count('id'))
        .order_by('-total', 'lotacao__nome')[:8]
    )

    sem_cargo = funcionarios.filter(cargo__isnull=True).count()
    sem_lotacao = funcionarios.filter(lotacao__isnull=True).count()
    sem_cpf = funcionarios.filter(Q(cpf__isnull=True) | Q(cpf='')).count()

    total_cargos = Cargo.objects.filter(empresa=empresa_ativa).count()
    total_lotacoes = Lotacao.objects.filter(empresa=empresa_ativa).count()

    context = {
        'total_funcionarios': total_funcionarios,
        'total_ativos': total_ativos,
        'total_admitidos': total_admitidos,
        'total_afastados': total_afastados,
        'total_ferias': total_ferias,
        'total_demitidos': total_demitidos,
        'admitidos_recentes': admitidos_recentes,
        'aniversariantes_mes': aniversariantes_mes,
        'cargos_resumo': cargos_resumo,
        'lotacoes_resumo': lotacoes_resumo,
        'sem_cargo': sem_cargo,
        'sem_lotacao': sem_lotacao,
        'sem_cpf': sem_cpf,
        'total_cargos': total_cargos,
        'total_lotacoes': total_lotacoes,
    }
    return render(request, 'rh/dashboard.html', context)


def lista_funcionarios(request):
    empresa_ativa = getattr(request, 'empresa_ativa', None)

    funcionarios = Funcionario.objects.select_related(
        'empresa',
        'cargo',
        'lotacao',
        'tipo_contrato',
    )

    if empresa_ativa:
        funcionarios = funcionarios.filter(empresa=empresa_ativa)
    else:
        funcionarios = funcionarios.none()

    q = request.GET.get('q')
    cargo_id = request.GET.get('cargo')
    lotacao_id = request.GET.get('lotacao')
    situacao = request.GET.get('situacao')

    if q:
        funcionarios = funcionarios.filter(
            Q(nome__icontains=q) |
            Q(cpf__icontains=q) |
            Q(matricula__icontains=q)
        )

    if cargo_id:
        funcionarios = funcionarios.filter(cargo_id=cargo_id)

    if lotacao_id:
        funcionarios = funcionarios.filter(lotacao_id=lotacao_id)

    if situacao:
        if situacao != 'todos':
            funcionarios = funcionarios.filter(situacao_atual=situacao)
    else:
        funcionarios = funcionarios.filter(situacao_atual='admitido')

    cargos = Cargo.objects.all()
    lotacoes = Lotacao.objects.all()

    if empresa_ativa:
        cargos = cargos.filter(empresa=empresa_ativa)
        lotacoes = lotacoes.filter(empresa=empresa_ativa)
    else:
        cargos = cargos.none()
        lotacoes = lotacoes.none()

    funcionarios = funcionarios.order_by('nome')

    context = {
        'funcionarios': funcionarios,
        'cargos': cargos.order_by('nome'),
        'lotacoes': lotacoes.order_by('nome'),
        'total_funcionarios_filtrados': funcionarios.count(),
    }
    return render(request, 'rh/funcionarios/lista.html', context)

def criar_funcionario(request):
    empresa_ativa = getattr(request, 'empresa_ativa', None)

    if not empresa_ativa:
        messages.warning(request, 'Selecione uma empresa antes de cadastrar funcionários.')
        return redirect('selecionar_empresa')

    if request.method == 'POST':
        form = FuncionarioForm(request.POST, request.FILES, empresa_ativa=empresa_ativa)
        formset = DependenteFormSet(request.POST, prefix='dependentes')

        if form.is_valid() and formset.is_valid():
            funcionario = form.save(commit=False)
            funcionario.empresa = empresa_ativa
            funcionario.save()

            formset.instance = funcionario
            formset.save()

            messages.success(request, 'Funcionário cadastrado com sucesso.')
            return redirect('rh:lista_funcionarios')
    else:
        form = FuncionarioForm(empresa_ativa=empresa_ativa)
        formset = DependenteFormSet(prefix='dependentes')

    context = {
        'form': form,
        'formset': formset,
        'titulo': 'Novo Funcionário',
    }
    return render(request, 'rh/funcionarios/form.html', context)


def editar_funcionario(request, pk):
    empresa_ativa = getattr(request, 'empresa_ativa', None)

    if not empresa_ativa:
        messages.warning(request, 'Selecione uma empresa antes de continuar.')
        return redirect('selecionar_empresa')

    funcionario = get_object_or_404(
        Funcionario,
        pk=pk,
        empresa=empresa_ativa
    )

    if request.method == 'POST':
        form = FuncionarioForm(
            request.POST,
            request.FILES,
            instance=funcionario,
            empresa_ativa=empresa_ativa
        )
        formset = DependenteFormSet(
            request.POST,
            instance=funcionario,
            prefix='dependentes'
        )

        if form.is_valid() and formset.is_valid():
            funcionario = form.save(commit=False)
            funcionario.empresa = empresa_ativa
            funcionario.save()
            formset.save()

            messages.success(request, 'Funcionário atualizado com sucesso.')
            return redirect('rh:lista_funcionarios')
    else:
        form = FuncionarioForm(instance=funcionario, empresa_ativa=empresa_ativa)
        formset = DependenteFormSet(instance=funcionario, prefix='dependentes')

    context = {
        'form': form,
        'formset': formset,
        'titulo': 'Editar Funcionário',
        'funcionario': funcionario,
    }
    return render(request, 'rh/funcionarios/form.html', context)


def detalhar_funcionario(request, pk):
    empresa_ativa = getattr(request, 'empresa_ativa', None)

    if not empresa_ativa:
        messages.warning(request, 'Selecione uma empresa antes de continuar.')
        return redirect('selecionar_empresa')

    funcionario = get_object_or_404(
        Funcionario.objects.select_related(
            'empresa',
            'cargo',
            'lotacao',
            'tipo_contrato',
            'banco',
        ).prefetch_related('dependentes'),
        pk=pk,
        empresa=empresa_ativa
    )

    context = {
        'funcionario': funcionario
    }
    return render(request, 'rh/funcionarios/detalhes.html', context)


def excluir_funcionario(request, pk):
    empresa_ativa = getattr(request, 'empresa_ativa', None)

    if not empresa_ativa:
        messages.warning(request, 'Selecione uma empresa antes de continuar.')
        return redirect('selecionar_empresa')

    funcionario = get_object_or_404(
        Funcionario,
        pk=pk,
        empresa=empresa_ativa
    )

    if request.method == 'POST':
        funcionario.delete()
        messages.success(request, 'Funcionário excluído com sucesso.')
        return redirect('rh:lista_funcionarios')

    context = {
        'funcionario': funcionario
    }
    return render(request, 'rh/funcionarios/confirmar_exclusao.html', context)


def lista_cargos(request):
    empresa_ativa = getattr(request, 'empresa_ativa', None)

    if not empresa_ativa:
        messages.warning(request, 'Selecione uma empresa para visualizar os cargos.')
        return redirect('selecionar_empresa')

    q = request.GET.get('q', '').strip()

    cargos = Cargo.objects.filter(empresa=empresa_ativa)

    if q:
        cargos = cargos.filter(nome__icontains=q)

    cargos = cargos.annotate(total_funcionarios=Count('funcionarios')).order_by('nome')

    context = {
        'cargos': cargos,
        'q': q,
    }
    return render(request, 'rh/cargos/lista.html', context)


def criar_cargo(request):
    empresa_ativa = getattr(request, 'empresa_ativa', None)

    if not empresa_ativa:
        messages.warning(request, 'Selecione uma empresa antes de cadastrar cargos.')
        return redirect('selecionar_empresa')

    if request.method == 'POST':
        form = CargoForm(request.POST)
        if form.is_valid():
            cargo = form.save(commit=False)
            cargo.empresa = empresa_ativa
            cargo.save()
            messages.success(request, 'Cargo cadastrado com sucesso.')
            return redirect('rh:lista_cargos')
    else:
        form = CargoForm()

    context = {
        'form': form,
        'titulo': 'Novo Cargo',
        'subtitulo': 'Cadastre um novo cargo para a empresa ativa.',
    }
    return render(request, 'rh/cargos/form.html', context)


def editar_cargo(request, pk):
    empresa_ativa = getattr(request, 'empresa_ativa', None)

    if not empresa_ativa:
        messages.warning(request, 'Selecione uma empresa antes de continuar.')
        return redirect('selecionar_empresa')

    cargo = get_object_or_404(Cargo, pk=pk, empresa=empresa_ativa)

    if request.method == 'POST':
        form = CargoForm(request.POST, instance=cargo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cargo atualizado com sucesso.')
            return redirect('rh:lista_cargos')
    else:
        form = CargoForm(instance=cargo)

    context = {
        'form': form,
        'titulo': 'Editar Cargo',
        'subtitulo': 'Atualize as informações do cargo.',
        'cargo': cargo,
    }
    return render(request, 'rh/cargos/form.html', context)


def excluir_cargo(request, pk):
    empresa_ativa = getattr(request, 'empresa_ativa', None)

    if not empresa_ativa:
        messages.warning(request, 'Selecione uma empresa antes de continuar.')
        return redirect('selecionar_empresa')

    cargo = get_object_or_404(Cargo, pk=pk, empresa=empresa_ativa)

    if request.method == 'POST':
        if cargo.funcionarios.exists():
            messages.error(
                request,
                'Este cargo não pode ser excluído porque existem funcionários vinculados a ele.'
            )
            return redirect('rh:lista_cargos')

        cargo.delete()
        messages.success(request, 'Cargo excluído com sucesso.')
        return redirect('rh:lista_cargos')

    context = {
        'cargo': cargo,
    }
    return render(request, 'rh/cargos/confirmar_exclusao.html', context)


def lista_lotacoes(request):
    empresa_ativa = getattr(request, 'empresa_ativa', None)

    if not empresa_ativa:
        messages.warning(request, 'Selecione uma empresa.')
        return redirect('selecionar_empresa')

    q = request.GET.get('q', '').strip()

    lotacoes = Lotacao.objects.filter(empresa=empresa_ativa)

    if q:
        lotacoes = lotacoes.filter(nome__icontains=q)

    lotacoes = lotacoes.annotate(total_funcionarios=Count('funcionarios')).order_by('nome')

    context = {
        'lotacoes': lotacoes,
        'q': q
    }

    return render(request, 'rh/lotacoes/lista.html', context)


def criar_lotacao(request):
    empresa_ativa = getattr(request, 'empresa_ativa', None)

    if not empresa_ativa:
        messages.warning(request, 'Selecione uma empresa.')
        return redirect('selecionar_empresa')

    if request.method == 'POST':
        form = LotacaoForm(request.POST)

        if form.is_valid():
            lotacao = form.save(commit=False)
            lotacao.empresa = empresa_ativa
            lotacao.save()

            messages.success(request, 'Lotação cadastrada com sucesso.')
            return redirect('rh:lista_lotacoes')
    else:
        form = LotacaoForm()

    context = {
        'form': form,
        'titulo': 'Nova Lotação',
        'subtitulo': 'Cadastre uma nova lotação'
    }

    return render(request, 'rh/lotacoes/form.html', context)


def editar_lotacao(request, pk):
    empresa_ativa = getattr(request, 'empresa_ativa', None)

    if not empresa_ativa:
        messages.warning(request, 'Selecione uma empresa.')
        return redirect('selecionar_empresa')

    lotacao = get_object_or_404(
        Lotacao,
        pk=pk,
        empresa=empresa_ativa
    )

    if request.method == 'POST':
        form = LotacaoForm(request.POST, instance=lotacao)

        if form.is_valid():
            form.save()
            messages.success(request, 'Lotação atualizada com sucesso.')
            return redirect('rh:lista_lotacoes')
    else:
        form = LotacaoForm(instance=lotacao)

    context = {
        'form': form,
        'titulo': 'Editar Lotação',
        'subtitulo': 'Atualize os dados da lotação'
    }

    return render(request, 'rh/lotacoes/form.html', context)


def excluir_lotacao(request, pk):
    empresa_ativa = getattr(request, 'empresa_ativa', None)

    if not empresa_ativa:
        messages.warning(request, 'Selecione uma empresa.')
        return redirect('selecionar_empresa')

    lotacao = get_object_or_404(
        Lotacao,
        pk=pk,
        empresa=empresa_ativa
    )

    if request.method == 'POST':
        if lotacao.funcionarios.exists():
            messages.error(
                request,
                'Esta lotação possui funcionários vinculados.'
            )
            return redirect('rh:lista_lotacoes')

        lotacao.delete()
        messages.success(request, 'Lotação excluída com sucesso.')
        return redirect('rh:lista_lotacoes')

    context = {
        'lotacao': lotacao
    }

    return render(request, 'rh/lotacoes/confirmar_exclusao.html', context)