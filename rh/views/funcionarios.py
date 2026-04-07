from datetime import date

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.registry import audit_rh

from core.urlutils import redirect_empresa

from ..forms import (
    AfastamentoFuncionarioFormSet,
    ASOFuncionarioFormSet,
    AtestadoLicencaFuncionarioFormSet,
    CertificadoFuncionarioFormSet,
    DependenteFormSet,
    FeriasFuncionarioFormSet,
    FuncionarioAdmissaoForm,
    FuncionarioDadosPessoaisForm,
    FuncionarioDemissaoForm,
    FuncionarioForm,
    FuncionarioOutrosForm,
    OcorrenciaSaudeFuncionarioFormSet,
    PCMSOFuncionarioFormSet,
)
from ..models import Cargo, Funcionario, Lotacao, TipoContrato
from .anexos import secao_anexos_context
from .base import (
    _empresa_ativa_or_redirect,
    _get_form_kwargs,
    _montar_formsets_funcionario,
    _salvar_todos_formsets,
    _todos_formsets_validos,
)


# ==========================================================
# LISTA PADRÃO DE FUNCIONÁRIOS
# ==========================================================
def lista_funcionarios(request):
    """
    Lista principal de funcionários do RH.

    Regras atuais:
    - filtra pela empresa ativa
    - permite filtro por nome, cargo, lotação, situação e grupo
    - por padrão exibe apenas admitidos
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para visualizar os funcionários.'
    )
    if redirect_response:
        return redirect_response

    hoje = date.today()

    funcionarios = Funcionario.objects.filter(
        empresa=empresa_ativa
    ).select_related(
        'empresa',
        'cargo',
        'lotacao',
        'tipo_contrato',
    )

    nome = request.GET.get('nome', '').strip()
    cargo_id = request.GET.get('cargo', '').strip()
    lotacao_id = request.GET.get('lotacao', '').strip()
    situacao = request.GET.get('situacao', '').strip()
    grupo = request.GET.get('grupo', '').strip()

    if nome:
        funcionarios = funcionarios.filter(
            Q(nome__icontains=nome) |
            Q(cpf__icontains=nome) |
            Q(pis__icontains=nome) |
            Q(matricula__icontains=nome)
        )

    if cargo_id:
        funcionarios = funcionarios.filter(cargo_id=cargo_id)

    if lotacao_id:
        funcionarios = funcionarios.filter(lotacao_id=lotacao_id)

    if situacao and situacao != 'todos':
        if situacao == 'demitido':
            # Demitidos são identificados pela data_demissao (mesmo que situacao_atual vire inativo)
            funcionarios = funcionarios.filter(data_demissao__isnull=False)
        else:
            funcionarios = funcionarios.filter(situacao_atual=situacao)
    elif grupo == 'todos':
        # Por padrão, não exibe desativados; só aparecem se filtrar explicitamente.
        funcionarios = funcionarios.exclude(situacao_atual__in=['demitido', 'inativo'])
    elif grupo == 'ferias':
        funcionarios = funcionarios.filter(
            ferias__gozo_inicio__lte=hoje,
            ferias__gozo_fim__gte=hoje,
        ).distinct()
    elif grupo == 'experiencia':
        funcionarios = funcionarios.filter(
            data_admissao__isnull=False,
            data_admissao__lte=hoje,
            fim_prorrogacao__isnull=False,
            fim_prorrogacao__gte=hoje,
        ).distinct()
    elif grupo == 'aviso':
        funcionarios = funcionarios.filter(
            data_inicio_aviso__isnull=False,
            data_fim_aviso__isnull=False,
            data_inicio_aviso__lte=hoje,
            data_fim_aviso__gte=hoje,
        )
    else:
        funcionarios = funcionarios.filter(situacao_atual='admitido')

    cargos = Cargo.objects.filter(empresa=empresa_ativa).order_by('nome')
    lotacoes = Lotacao.objects.filter(empresa=empresa_ativa).order_by('nome')

    context = {
        'funcionarios': funcionarios.order_by('nome'),
        'cargos': cargos,
        'lotacoes': lotacoes,
        'status_choices': Funcionario.STATUS_CHOICES,
        'total_funcionarios_filtrados': funcionarios.count(),
    }
    return render(request, 'rh/funcionarios/lista.html', context)


# ==========================================================
# BUSCA AVANÇADA DE FUNCIONÁRIOS
# ==========================================================
def buscar_funcionarios(request):
    """
    Busca avançada de funcionários.

    Permite filtros por:
    - texto livre
    - cargo
    - lotação
    - situação
    - tipo de contrato
    - datas de admissão/demissão
    - aviso ativo
    - férias
    - afastamento
    - sem cargo / sem lotação
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para buscar funcionários.'
    )
    if redirect_response:
        return redirect_response

    hoje = date.today()

    funcionarios = Funcionario.objects.filter(
        empresa=empresa_ativa
    ).select_related(
        'empresa',
        'cargo',
        'lotacao',
        'tipo_contrato',
    ).prefetch_related('ferias', 'afastamentos')

    q = request.GET.get('q', '').strip()
    cargo_id = request.GET.get('cargo', '').strip()
    lotacao_id = request.GET.get('lotacao', '').strip()
    situacao = request.GET.get('situacao', '').strip()
    tipo_contrato_id = request.GET.get('tipo_contrato', '').strip()

    admissao_de = request.GET.get('admissao_de', '').strip()
    admissao_ate = request.GET.get('admissao_ate', '').strip()
    demissao_de = request.GET.get('demissao_de', '').strip()
    demissao_ate = request.GET.get('demissao_ate', '').strip()

    aviso_ativo = request.GET.get('aviso_ativo', '').strip()
    em_ferias = request.GET.get('em_ferias', '').strip()
    experiencia = request.GET.get('experiencia', '').strip()
    afastado = request.GET.get('afastado', '').strip()
    sem_cargo = request.GET.get('sem_cargo', '').strip()
    sem_lotacao = request.GET.get('sem_lotacao', '').strip()

    if q:
        funcionarios = funcionarios.filter(
            Q(nome__icontains=q) |
            Q(cpf__icontains=q) |
            Q(pis__icontains=q) |
            Q(matricula__icontains=q) |
            Q(rg__icontains=q)
        )

    if cargo_id:
        funcionarios = funcionarios.filter(cargo_id=cargo_id)

    if lotacao_id:
        funcionarios = funcionarios.filter(lotacao_id=lotacao_id)

    if situacao and situacao != 'todos':
        if situacao == 'desativados':
            # Inclui:
            # - inativos "manuais"
            # - demitidos legados (situacao_atual='demitido')
            # - demitidos atuais (data_demissao preenchida)
            funcionarios = funcionarios.filter(
                Q(situacao_atual__in=['inativo', 'demitido']) |
                Q(data_demissao__isnull=False)
            )
        elif situacao == 'demitido':
            funcionarios = funcionarios.filter(data_demissao__isnull=False)
        else:
            funcionarios = funcionarios.filter(situacao_atual=situacao)
    else:
        # Por padrão, não exibe demitidos/inativos na busca.
        # Eles só aparecem se o usuário filtrar explicitamente por situação.
        funcionarios = funcionarios.exclude(situacao_atual__in=['demitido', 'inativo'])

    if tipo_contrato_id:
        funcionarios = funcionarios.filter(tipo_contrato_id=tipo_contrato_id)

    if admissao_de:
        funcionarios = funcionarios.filter(data_admissao__gte=admissao_de)

    if admissao_ate:
        funcionarios = funcionarios.filter(data_admissao__lte=admissao_ate)

    if demissao_de:
        funcionarios = funcionarios.filter(data_demissao__gte=demissao_de)

    if demissao_ate:
        funcionarios = funcionarios.filter(data_demissao__lte=demissao_ate)

    if aviso_ativo == '1':
        funcionarios = funcionarios.filter(
            data_inicio_aviso__isnull=False,
            data_fim_aviso__isnull=False,
            data_inicio_aviso__lte=hoje,
            data_fim_aviso__gte=hoje,
        )

    if em_ferias == '1':
        funcionarios = funcionarios.filter(
            ferias__gozo_inicio__lte=hoje,
            ferias__gozo_fim__gte=hoje,
        ).distinct()

    if experiencia == '1':
        funcionarios = funcionarios.filter(
            data_admissao__isnull=False,
            data_admissao__lte=hoje,
            fim_prorrogacao__isnull=False,
            fim_prorrogacao__gte=hoje,
        ).distinct()

    if afastado == '1':
        funcionarios = funcionarios.filter(situacao_atual='afastado')

    if sem_cargo == '1':
        funcionarios = funcionarios.filter(cargo__isnull=True)

    if sem_lotacao == '1':
        funcionarios = funcionarios.filter(lotacao__isnull=True)

    funcionarios = funcionarios.order_by('nome').distinct()

    cargos = Cargo.objects.filter(empresa=empresa_ativa).order_by('nome')
    lotacoes = Lotacao.objects.filter(empresa=empresa_ativa).order_by('nome')
    tipos_contrato = TipoContrato.objects.filter(empresa=empresa_ativa).order_by('nome')

    context = {
        'funcionarios': funcionarios,
        'cargos': cargos,
        'lotacoes': lotacoes,
        'tipos_contrato': tipos_contrato,
        'status_choices': Funcionario.STATUS_CHOICES,
        'total_resultados': funcionarios.count(),
        'filtros_ativos': any([
            q, cargo_id, lotacao_id, situacao, tipo_contrato_id,
            admissao_de, admissao_ate, demissao_de, demissao_ate,
            aviso_ativo, em_ferias, experiencia, afastado, sem_cargo, sem_lotacao,
        ]),
    }
    return render(request, 'rh/funcionarios/buscar.html', context)


# ==========================================================
# CRIAÇÃO COMPLETA DE FUNCIONÁRIO
# ==========================================================
@transaction.atomic
def criar_funcionario(request):
    """
    Cadastro completo de funcionário com form principal + formsets.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de cadastrar funcionários.'
    )
    if redirect_response:
        return redirect_response

    if request.method == 'POST':
        form = FuncionarioForm(
            request.POST,
            request.FILES,
            empresa_ativa=empresa_ativa,
        )
        formsets = _montar_formsets_funcionario(request=request, instance=None)

        if form.is_valid() and _todos_formsets_validos(formsets):
            funcionario = form.save(commit=False)
            funcionario.empresa = empresa_ativa
            funcionario.save()

            _salvar_todos_formsets(funcionario, formsets)

            audit_rh(
                request,
                'create',
                f'Funcionário "{funcionario.nome}" cadastrado (cadastro completo).',
                {'funcionario_id': funcionario.pk},
            )
            messages.success(request, 'Funcionário cadastrado com sucesso.')
            return redirect_empresa(request, 'rh:detalhes_funcionario', pk=funcionario.pk)
    else:
        form = FuncionarioForm(empresa_ativa=empresa_ativa)
        formsets = _montar_formsets_funcionario()

    context = {
        'form': form,
        'titulo': 'Novo Funcionário',
        'subtitulo': 'Preencha os dados do colaborador e seus históricos.',
        **formsets,
    }
    return render(request, 'rh/funcionarios/form.html', context)


# ==========================================================
# FORMS PRINCIPAIS DA EDIÇÃO POR SEÇÃO
# ==========================================================
def _montar_forms_funcionario(request, empresa_ativa, funcionario):
    """
    Monta os forms principais usados na edição por seção.
    """
    kwargs = _get_form_kwargs(request, empresa_ativa, instance=funcionario)

    return {
        'form_pessoais': FuncionarioDadosPessoaisForm(**kwargs),
        'form_admissao': FuncionarioAdmissaoForm(**kwargs),
        'form_demissao': FuncionarioDemissaoForm(**kwargs),
        'form_outros': FuncionarioOutrosForm(**kwargs),
    }


# ==========================================================
# FORMSETS DA EDIÇÃO POR SEÇÃO
# ==========================================================
def _montar_formsets_funcionario_por_secao(request=None, instance=None, secao_post=None):
    """
    Monta os formsets por seção.

    Regra:
    - se for POST, somente a seção enviada recebe POST/FILES
    - as outras permanecem em modo leitura/GET
    - isso evita invalidar a tela inteira ao salvar uma única seção
    """
    is_post = request is not None and request.method == 'POST'

    def bind_if(secao_nome, formset_class, prefix):
        if is_post and secao_post == secao_nome:
            return formset_class(
                request.POST,
                request.FILES,
                instance=instance,
                prefix=prefix,
            )
        return formset_class(
            instance=instance,
            prefix=prefix,
        )

    return {
        'ferias_formset': bind_if('ferias', FeriasFuncionarioFormSet, 'ferias'),
        'afastamento_formset': bind_if('afastamentos', AfastamentoFuncionarioFormSet, 'afastamentos'),
        'dependente_formset': bind_if('dependentes', DependenteFormSet, 'dependentes'),
        'aso_formset': bind_if('saude', ASOFuncionarioFormSet, 'asos'),
        'certificado_formset': bind_if('saude', CertificadoFuncionarioFormSet, 'certificados'),
        'pcmso_formset': bind_if('saude', PCMSOFuncionarioFormSet, 'pcmso'),
        'atestado_licenca_formset': bind_if('saude', AtestadoLicencaFuncionarioFormSet, 'atestados_licencas'),
        'ocorrencia_saude_formset': bind_if('saude', OcorrenciaSaudeFuncionarioFormSet, 'ocorrencias_saude'),
    }


# ==========================================================
# SALVAR UMA ÚNICA SEÇÃO
# ==========================================================
def _salvar_secao_funcionario(secao, forms, formsets, funcionario, empresa_ativa):
    """
    Salva apenas a seção enviada.

    Retorno:
        (True, 'mensagem')  -> sucesso
        (False, 'mensagem') -> erro de validação
    """

    if secao == 'pessoais':
        form = forms['form_pessoais']
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa_ativa
            obj.save()
            return True, 'Dados pessoais atualizados com sucesso.'
        return False, 'Corrija os erros em Dados Pessoais.'

    if secao == 'admissao':
        form = forms['form_admissao']
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa_ativa
            obj.save()
            return True, 'Dados de admissão atualizados com sucesso.'
        return False, 'Corrija os erros em Admissão.'

    if secao == 'demissao':
        form = forms['form_demissao']
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa_ativa

            if obj.data_demissao:
                obj.situacao_atual = 'inativo'
            elif obj.situacao_atual == 'inativo':
                obj.situacao_atual = 'admitido'

            obj.save()
            return True, 'Dados de demissão atualizados com sucesso.'
        return False, 'Corrija os erros em Demissão.'

    if secao == 'outros':
        form = forms['form_outros']
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa_ativa
            obj.save()
            return True, 'Outros dados atualizados com sucesso.'
        return False, 'Corrija os erros em Outros Dados.'

    if secao == 'ferias':
        formset = formsets['ferias_formset']
        if formset.is_valid():
            formset.instance = funcionario
            formset.save()
            return True, 'Férias atualizadas com sucesso.'
        return False, 'Corrija os erros em Férias.'

    if secao == 'afastamentos':
        formset = formsets['afastamento_formset']
        if formset.is_valid():
            formset.instance = funcionario
            formset.save()
            return True, 'Afastamentos atualizados com sucesso.'
        return False, 'Corrija os erros em Afastamentos.'

    if secao == 'dependentes':
        formset = formsets['dependente_formset']
        if formset.is_valid():
            formset.instance = funcionario
            formset.save()
            return True, 'Dependentes atualizados com sucesso.'
        return False, 'Corrija os erros em Dependentes.'

    if secao == 'saude':
        formsets_saude = [
            formsets['aso_formset'],
            formsets['certificado_formset'],
            formsets['pcmso_formset'],
            formsets['atestado_licenca_formset'],
            formsets['ocorrencia_saude_formset'],
        ]

        if all(fs.is_valid() for fs in formsets_saude):
            for fs in formsets_saude:
                fs.instance = funcionario
                fs.save()
            return True, 'Dados de saúde atualizados com sucesso.'
        return False, 'Corrija os erros em Saúde.'

    return False, 'Seção inválida.'


# ==========================================================
# EDIÇÃO COMPLETA POR SEÇÕES
# ==========================================================
@transaction.atomic
def editar_funcionario(request, pk):
    """
    Edita o funcionário em uma tela única organizada por seções.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(
        Funcionario.objects.select_related(
            'empresa',
            'cargo',
            'lotacao',
            'tipo_contrato',
            'banco',
        ).prefetch_related(
            'dependentes',
            'ferias',
            'afastamentos',
            'asos',
            'certificados',
            'pcmso_registros',
            'atestados_licencas',
            'ocorrencias_saude',
        ),
        pk=pk,
        empresa=empresa_ativa,
    )

    secao = request.POST.get('secao') if request.method == 'POST' else 'pessoais'

    forms = _montar_forms_funcionario(request, empresa_ativa, funcionario)
    formsets = _montar_formsets_funcionario_por_secao(
        request=request,
        instance=funcionario,
        secao_post=secao,
    )

    if request.method == 'POST':
        salvou, mensagem = _salvar_secao_funcionario(
            secao=secao,
            forms=forms,
            formsets=formsets,
            funcionario=funcionario,
            empresa_ativa=empresa_ativa,
        )

        if salvou:
            audit_rh(
                request,
                'update',
                f'Funcionário "{funcionario.nome}": seção "{secao}" atualizada.',
                {'funcionario_id': funcionario.pk, 'secao': secao},
            )
            messages.success(request, mensagem)
            return redirect_empresa(request, 'rh:editar_funcionario', pk=funcionario.pk)

        messages.error(request, mensagem)

        # Recria os formulários para manter a tela completa após erro
        forms = _montar_forms_funcionario(request, empresa_ativa, funcionario)
        formsets = _montar_formsets_funcionario_por_secao(
            request=request,
            instance=funcionario,
            secao_post=secao,
        )
    else:
        forms = _montar_forms_funcionario(request, empresa_ativa, funcionario)
        formsets = _montar_formsets_funcionario_por_secao(
            request=None,
            instance=funcionario,
            secao_post=None,
        )

    context = {
        'titulo': 'Editar Funcionário',
        'subtitulo': f'Atualize os dados de {funcionario.nome} por seção.',
        'funcionario': funcionario,
        'secao_ativa': secao,
        **forms,
        **formsets,
    }
    return render(request, 'rh/funcionarios/form.html', context)


# ==========================================================
# DETALHES DO FUNCIONÁRIO
# ==========================================================
def detalhes_funcionario(request, pk):
    """
    Tela de detalhes completa do funcionário.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(
        Funcionario.objects.select_related(
            'empresa',
            'cargo',
            'lotacao',
            'tipo_contrato',
            'banco',
        ).prefetch_related(
            'dependentes',
            'ferias',
            'afastamentos',
            'asos',
            'certificados',
            'pcmso_registros',
            'atestados_licencas',
            'ocorrencias_saude',
        ),
        pk=pk,
        empresa=empresa_ativa,
    )

    data_admissao = funcionario.data_admissao
    data_demissao = funcionario.data_demissao

    precisa_exame_demissional = False
    exame_info_indisponivel = False

    if data_admissao and data_demissao:
        precisa_exame_demissional = (data_demissao - data_admissao).days > 90
    else:
        exame_info_indisponivel = True

    historicos = funcionario.historicos.select_related('usuario').all()

    secoes_validas = {
        'pessoais',
        'admissao',
        'ferias',
        'afastamentos',
        'demissao',
        'dependentes',
        'saude',
        'bancarios',
        'anexos',
        'outros',
        'historico',
    }
    secao_inicial = (request.GET.get('secao') or 'pessoais').strip().lower()
    if secao_inicial not in secoes_validas:
        secao_inicial = 'pessoais'

    saude_validas = {'aso', 'certificados', 'pcmso', 'atestados', 'ocorrencias'}
    saude_inicial = (request.GET.get('saude') or 'aso').strip().lower()
    if saude_inicial not in saude_validas:
        saude_inicial = 'aso'

    context = {
        'funcionario': funcionario,
        'precisa_exame_demissional': precisa_exame_demissional,
        'exame_info_indisponivel': exame_info_indisponivel,
        'historicos': historicos,
        'secao_inicial': secao_inicial,
        'saude_inicial': saude_inicial,
    }
    context.update(secao_anexos_context(funcionario))

    return render(request, 'rh/funcionarios/detalhes.html', context)


# Compatibilidade com nome antigo de view
detalhar_funcionario = detalhes_funcionario


# ==========================================================
# EXCLUIR FUNCIONÁRIO
# ==========================================================
def excluir_funcionario(request, pk):
    """
    Exclui um funcionário da empresa ativa.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(
        Funcionario,
        pk=pk,
        empresa=empresa_ativa,
    )

    if request.method == 'POST':
        nome = funcionario.nome
        fid = funcionario.pk
        funcionario.delete()
        audit_rh(
            request,
            'delete',
            f'Funcionário "{nome}" excluído.',
            {'funcionario_id': fid},
        )
        messages.success(request, 'Funcionário excluído com sucesso.')
        return redirect_empresa(request, 'rh:lista_funcionarios')

    return render(
        request,
        'rh/funcionarios/excluir.html',
        {'funcionario': funcionario},
    )