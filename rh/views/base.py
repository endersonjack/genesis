from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from ..forms import (
    DependenteFormSet,
    FeriasFuncionarioFormSet,
    AfastamentoFuncionarioFormSet,
    ASOFuncionarioFormSet,
    CertificadoFuncionarioFormSet,
    PCMSOFuncionarioFormSet,
    AtestadoLicencaFuncionarioFormSet,
    OcorrenciaSaudeFuncionarioFormSet,
)
from ..models import Funcionario


# ==========================================================
# EMPRESA ATIVA
# ==========================================================
def _empresa_ativa_or_redirect(request, mensagem='Selecione uma empresa para continuar.'):
    """
    Retorna a empresa ativa da request.

    Uso:
        empresa_ativa, redirect_response = _empresa_ativa_or_redirect(request)
        if redirect_response:
            return redirect_response

    Retorno:
        - (empresa_ativa, None), quando existir empresa ativa
        - (None, redirect(...)), quando não existir
    """
    empresa_ativa = getattr(request, 'empresa_ativa', None)

    if not empresa_ativa:
        messages.warning(request, mensagem)
        return None, redirect('selecionar_empresa')

    return empresa_ativa, None


# ==========================================================
# FUNCIONÁRIO VINCULADO À EMPRESA ATIVA
# ==========================================================
def _get_funcionario_empresa(request, pk, mensagem='Selecione uma empresa antes de continuar.'):
    """
    Busca um funcionário garantindo que ele pertença à empresa ativa.

    Isso evita acessar funcionário de outra empresa por URL direta.

    Uso:
        funcionario, redirect_response = _get_funcionario_empresa(request, pk)
        if redirect_response:
            return redirect_response
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(request, mensagem)

    if redirect_response:
        return None, redirect_response

    funcionario = get_object_or_404(
        Funcionario,
        pk=pk,
        empresa=empresa_ativa,
    )

    return funcionario, None


# ==========================================================
# KWARGS PADRÃO PARA FORMS
# ==========================================================
def _get_form_kwargs(request, empresa_ativa, instance=None):
    """
    Monta os kwargs padrão para formulários do RH.

    Em GET:
        retorna apenas instance + empresa_ativa

    Em POST:
        retorna também data e files

    Uso:
        kwargs = _get_form_kwargs(request, empresa_ativa, instance=funcionario)
        form = MeuForm(**kwargs)
    """
    kwargs = {
        'instance': instance,
        'empresa_ativa': empresa_ativa,
    }

    if request.method == 'POST':
        kwargs['data'] = request.POST
        kwargs['files'] = request.FILES

    return kwargs


# ==========================================================
# FORMSETS GERAIS DO FUNCIONÁRIO
# ==========================================================
def _montar_formsets_funcionario(request=None, instance=None):
    """
    Centraliza a criação dos formsets usados no create/edit completo do funcionário.

    Quando request for POST:
        vincula request.POST e request.FILES

    Quando request for GET ou None:
        monta os formsets apenas com instance

    Observação:
        Essa versão é ideal para a tela completa de cadastro/edição.
        Para edição por seção, você já tem outra lógica mais específica,
        que deve ficar no arquivo de funcionários.
    """
    is_post = request is not None and request.method == 'POST'
    post_data = request.POST if is_post else None
    file_data = request.FILES if is_post else None

    return {
        'dependente_formset': DependenteFormSet(
            post_data,
            file_data,
            instance=instance,
            prefix='dependentes',
        ),
        'ferias_formset': FeriasFuncionarioFormSet(
            post_data,
            file_data,
            instance=instance,
            prefix='ferias',
        ),
        'afastamento_formset': AfastamentoFuncionarioFormSet(
            post_data,
            file_data,
            instance=instance,
            prefix='afastamentos',
        ),
        'aso_formset': ASOFuncionarioFormSet(
            post_data,
            file_data,
            instance=instance,
            prefix='asos',
        ),
        'certificado_formset': CertificadoFuncionarioFormSet(
            post_data,
            file_data,
            instance=instance,
            prefix='certificados',
        ),
        'pcmso_formset': PCMSOFuncionarioFormSet(
            post_data,
            file_data,
            instance=instance,
            prefix='pcmso',
        ),
        'atestado_licenca_formset': AtestadoLicencaFuncionarioFormSet(
            post_data,
            file_data,
            instance=instance,
            prefix='atestados_licencas',
        ),
        'ocorrencia_saude_formset': OcorrenciaSaudeFuncionarioFormSet(
            post_data,
            file_data,
            instance=instance,
            prefix='ocorrencias_saude',
        ),
    }


# ==========================================================
# VALIDAÇÃO DOS FORMSETS
# ==========================================================
def _todos_formsets_validos(formsets_dict):
    """
    Verifica se todos os formsets recebidos são válidos.

    Retorna:
        True  -> se todos forem válidos
        False -> se algum falhar

    Uso:
        if form.is_valid() and _todos_formsets_validos(formsets):
            ...
    """
    return all(formset.is_valid() for formset in formsets_dict.values())


# ==========================================================
# SALVAMENTO DOS FORMSETS
# ==========================================================
def _salvar_todos_formsets(funcionario, formsets_dict):
    """
    Salva todos os formsets vinculando-os ao funcionário informado.

    Uso comum:
        funcionario = form.save(commit=False)
        funcionario.empresa = empresa_ativa
        funcionario.save()

        _salvar_todos_formsets(funcionario, formsets)
    """
    for formset in formsets_dict.values():
        formset.instance = funcionario
        formset.save()