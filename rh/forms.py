from django import forms
from django.forms import inlineformset_factory

from .models import *


class DateInput(forms.DateInput):
    input_type = 'date'


class BaseStyledModelForm(forms.ModelForm):
    """
    Base para padronizar classes CSS dos campos.
    """

    textarea_rows_default = 3

    def apply_bootstrap_classes(self):
        for field_name, field in self.fields.items():
            widget = field.widget

            if isinstance(widget, forms.CheckboxInput):
                css = 'form-check-input'
            elif isinstance(widget, forms.Select):
                css = 'form-select'
            elif isinstance(widget, forms.ClearableFileInput):
                css = 'form-control'
            else:
                css = 'form-control'

            current = widget.attrs.get('class', '')
            widget.attrs['class'] = f'{current} {css}'.strip()

    def filter_empresa_queryset(self, empresa_ativa):
        if not empresa_ativa:
            return

        if 'cargo' in self.fields:
            self.fields['cargo'].queryset = Cargo.objects.filter(
                empresa=empresa_ativa
            ).order_by('nome')

        if 'lotacao' in self.fields:
            self.fields['lotacao'].queryset = Lotacao.objects.filter(
                empresa=empresa_ativa
            ).order_by('nome')

        if 'tipo_contrato' in self.fields:
            self.fields['tipo_contrato'].queryset = TipoContrato.objects.filter(
                empresa=empresa_ativa
            ).order_by('nome')


class FuncionarioForm(BaseStyledModelForm):
    """
    Formulário completo.
    Pode continuar sendo usado no create ou onde você quiser editar tudo de uma vez.
    """

    class Meta:
        model = Funcionario
        fields = [
            'matricula',
            'foto',

            # dados pessoais
            'nome',
            'cpf',
            'pis',
            'rg',
            'cnh',
            'categoria_cnh',
            'nacionalidade',
            'data_nascimento',
            'endereco_completo',
            'telefone_1',
            'telefone_2',
            'estado_civil',
            'sexo',
            'nome_mae',
            'nome_pai',

            # admissão / vínculo
            'cargo',
            'lotacao',
            'situacao_atual',
            'data_admissao',
            'inicio_prorrogacao',
            'fim_prorrogacao',
            'tipo_contrato',
            'salario',
            'adicional',
            'recebe_vale_transporte',
            'valor_vale_transporte',
            'contribuinte_sindical',
            'recebe_salario_familia',
            'data_ultimo_exame',
            'responsavel',

            # demissão
            'data_demissao',
            'tipo_demissao',
            'tipo_aviso',
            'data_inicio_aviso',
            'data_fim_aviso',
            'anexo_aviso',
            'precisa_exame_demissional',
            'rescisao_assinada',
            'observacoes_demissao',

            # dados bancários / outros
            'banco',
            'agencia',
            'tipo_conta',
            'operacao',
            'numero_conta',
            'tipo_pix',
            'pix',
            'e_social',
            'analfabeto',
            'observacoes',
        ]
        widgets = {
            'data_nascimento': DateInput(),
            'data_admissao': DateInput(),
            'inicio_prorrogacao': DateInput(),
            'fim_prorrogacao': DateInput(),
            'data_ultimo_exame': DateInput(),
            'data_demissao': DateInput(),
            'data_inicio_aviso': DateInput(),
            'data_fim_aviso': DateInput(),
            'observacoes': forms.Textarea(attrs={'rows': 4}),
            'observacoes_demissao': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        empresa_ativa = kwargs.pop('empresa_ativa', None)
        super().__init__(*args, **kwargs)

        obrigatorios = ['nome', 'cpf', 'situacao_atual', 'cargo']
        for nome, field in self.fields.items():
            field.required = nome in obrigatorios

        self.apply_bootstrap_classes()
        self.filter_empresa_queryset(empresa_ativa)


class FuncionarioDadosPessoaisForm(BaseStyledModelForm):
    class Meta:
        model = Funcionario
        fields = [
            'matricula',
            'foto',
            'nome',
            'cpf',
            'pis',
            'rg',
            'cnh',
            'categoria_cnh',
            'nacionalidade',
            'data_nascimento',
            'endereco_completo',
            'telefone_1',
            'telefone_2',
            'estado_civil',
            'sexo',
            'nome_mae',
            'nome_pai',
        ]
        widgets = {
            'data_nascimento': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }
            ),
            'endereco_completo': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop('empresa_ativa', None)
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()

        obrigatorios = ['nome', 'cpf']
        for nome, field in self.fields.items():
            field.required = nome in obrigatorios

        self.fields['data_nascimento'].input_formats = ['%Y-%m-%d']


class FuncionarioAdmissaoForm(BaseStyledModelForm):
    class Meta:
        model = Funcionario
        fields = [
            'cargo',
            'lotacao',
            'situacao_atual',
            'data_admissao',
            'inicio_prorrogacao',
            'fim_prorrogacao',
            'tipo_contrato',
            'salario',
            'adicional',
            'recebe_vale_transporte',
            'valor_vale_transporte',
            'contribuinte_sindical',
            'recebe_salario_familia',
            'data_ultimo_exame',
            'responsavel',
        ]
        widgets = {
            'data_admissao': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }
            ),
            'inicio_prorrogacao': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }
            ),
            'fim_prorrogacao': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }
            ),
            'data_ultimo_exame': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        empresa_ativa = kwargs.pop('empresa_ativa', None)
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()
        self.filter_empresa_queryset(empresa_ativa)

        obrigatorios = ['cargo', 'situacao_atual']
        for nome, field in self.fields.items():
            field.required = nome in obrigatorios


class FuncionarioDemissaoForm(BaseStyledModelForm):
    class Meta:
        model = Funcionario
        fields = [
            'data_demissao',
            'tipo_demissao',
            'tipo_aviso',
            'data_inicio_aviso',
            'data_fim_aviso',
            'anexo_aviso',
            'precisa_exame_demissional',
            'rescisao_assinada',
            'observacoes_demissao',
        ]
        widgets = {
            'data_demissao': DateInput(format='%Y-%m-%d'),
            'data_inicio_aviso': DateInput(format='%Y-%m-%d'),
            'data_fim_aviso': DateInput(format='%Y-%m-%d'),
            'observacoes_demissao': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop('empresa_ativa', None)
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()

        self.fields['data_demissao'].input_formats = ['%Y-%m-%d']
        self.fields['data_inicio_aviso'].input_formats = ['%Y-%m-%d']
        self.fields['data_fim_aviso'].input_formats = ['%Y-%m-%d']


class FuncionarioRecebeSalarioFamiliaForm(BaseStyledModelForm):
    """Campo do funcionário usado na seção Dependentes (edição por seção)."""

    class Meta:
        model = Funcionario
        fields = ['recebe_salario_familia']
        widgets = {
            'recebe_salario_familia': forms.CheckboxInput(
                attrs={'class': 'sf-dep-toggle-input'},
            ),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop('empresa_ativa', None)
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()
        self.fields['recebe_salario_familia'].widget.attrs['class'] = 'sf-dep-toggle-input'
        self.fields['recebe_salario_familia'].label = ''


class FuncionarioOutrosForm(BaseStyledModelForm):
    class Meta:
        model = Funcionario
        fields = [
            'banco',
            'agencia',
            'tipo_conta',
            'operacao',
            'numero_conta',
            'tipo_pix',
            'pix',
            'e_social',
            'analfabeto',
            'observacoes',
        ]
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop('empresa_ativa', None)
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()


class DependenteForm(BaseStyledModelForm):
    class Meta:
        model = Dependente
        fields = [
            'nome',
            'data_nascimento',
            'cpf',
            'parentesco',
        ]
        widgets = {
            'data_nascimento': DateInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()

    def clean_cpf(self):
        cpf = (self.cleaned_data.get('cpf') or '').strip()
        return cpf

DependenteFormSet = inlineformset_factory(
    Funcionario,
    Dependente,
    form=DependenteForm,
    extra=1,
    can_delete=True
)


class FeriasFuncionarioForm(BaseStyledModelForm):
    class Meta:
        model = FeriasFuncionario
        fields = [
            'periodo_aquisitivo_inicio',
            'periodo_aquisitivo_fim',
            'gozo_inicio',
            'gozo_fim',
            'teve_abono_pecuniario',
            'dias_abono_pecuniario',
            'observacoes',
        ]
        widgets = {
            'periodo_aquisitivo_inicio': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }),
            'periodo_aquisitivo_fim': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }),
            'gozo_inicio': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }),
            'gozo_fim': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()

class FeriasModalForm(FeriasFuncionarioForm):
    class Meta(FeriasFuncionarioForm.Meta):
        pass

    def clean(self):
        cleaned_data = super().clean()

        periodo_inicio = cleaned_data.get('periodo_aquisitivo_inicio')
        periodo_fim = cleaned_data.get('periodo_aquisitivo_fim')
        gozo_inicio = cleaned_data.get('gozo_inicio')
        gozo_fim = cleaned_data.get('gozo_fim')
        teve_abono = cleaned_data.get('teve_abono_pecuniario')
        dias_abono = cleaned_data.get('dias_abono_pecuniario')

        if periodo_inicio and periodo_fim and periodo_fim < periodo_inicio:
            self.add_error(
                'periodo_aquisitivo_fim',
                'A data final do período aquisitivo não pode ser menor que a inicial.'
            )

        if gozo_inicio and gozo_fim and gozo_fim < gozo_inicio:
            self.add_error(
                'gozo_fim',
                'A data final do gozo não pode ser menor que a inicial.'
            )

        if teve_abono and not dias_abono:
            self.add_error(
                'dias_abono_pecuniario',
                'Informe a quantidade de dias do abono pecuniário.'
            )

        if not teve_abono:
            cleaned_data['dias_abono_pecuniario'] = None

        return cleaned_data



FeriasFuncionarioFormSet = inlineformset_factory(
    Funcionario,
    FeriasFuncionario,
    form=FeriasFuncionarioForm,
    extra=1,
    can_delete=True
)


class AfastamentoFuncionarioForm(BaseStyledModelForm):
    class Meta:
        model = AfastamentoFuncionario
        fields = [
            'tipo',
            'data_afastamento',
            'previsao_retorno',
            'observacoes',
        ]
        widgets = {
            'data_afastamento': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }),
            'previsao_retorno': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        data_afastamento = cleaned_data.get('data_afastamento')
        previsao_retorno = cleaned_data.get('previsao_retorno')

        if data_afastamento and previsao_retorno and previsao_retorno < data_afastamento:
            self.add_error(
                'previsao_retorno',
                'A previsão de retorno não pode ser menor que a data do afastamento.'
            )

        return cleaned_data


AfastamentoFuncionarioFormSet = inlineformset_factory(
    Funcionario,
    AfastamentoFuncionario,
    form=AfastamentoFuncionarioForm,
    extra=1,
    can_delete=True
)


class ASOFuncionarioForm(BaseStyledModelForm):
    class Meta:
        model = ASOFuncionario
        fields = ['tipo', 'data', 'anexo']
        widgets = {
            'data': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()


ASOFuncionarioFormSet = inlineformset_factory(
    Funcionario,
    ASOFuncionario,
    form=ASOFuncionarioForm,
    extra=1,
    can_delete=True
)


class CertificadoFuncionarioForm(BaseStyledModelForm):
    class Meta:
        model = CertificadoFuncionario
        fields = ['tipo', 'data', 'anexo']
        widgets = {
            'data': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()


CertificadoFuncionarioFormSet = inlineformset_factory(
    Funcionario,
    CertificadoFuncionario,
    form=CertificadoFuncionarioForm,
    extra=1,
    can_delete=True
)


class PCMSOFuncionarioForm(BaseStyledModelForm):
    class Meta:
        model = PCMSOFuncionario
        fields = ['data_vencimento', 'anexo', 'observacoes']
        widgets = {
            'data_vencimento': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()


PCMSOFuncionarioFormSet = inlineformset_factory(
    Funcionario,
    PCMSOFuncionario,
    form=PCMSOFuncionarioForm,
    extra=1,
    can_delete=True
)


class AtestadoLicencaFuncionarioForm(BaseStyledModelForm):
    class Meta:
        model = AtestadoLicencaFuncionario
        fields = [
            'tipo',
            'data',
            'periodo_inicio',
            'periodo_fim',
            'anexo',
            'observacoes',
        ]
        widgets = {
            'data': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }),
            'periodo_inicio': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }),
            'periodo_fim': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()


AtestadoLicencaFuncionarioFormSet = inlineformset_factory(
    Funcionario,
    AtestadoLicencaFuncionario,
    form=AtestadoLicencaFuncionarioForm,
    extra=1,
    can_delete=True
)


class OcorrenciaSaudeFuncionarioForm(BaseStyledModelForm):
    class Meta:
        model = OcorrenciaSaudeFuncionario
        fields = ['tipo', 'descricao', 'origem', 'data', 'anexo']
        widgets = {
            'data': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }),
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()


OcorrenciaSaudeFuncionarioFormSet = inlineformset_factory(
    Funcionario,
    OcorrenciaSaudeFuncionario,
    form=OcorrenciaSaudeFuncionarioForm,
    extra=1,
    can_delete=True
)


class CargoForm(forms.ModelForm):
    class Meta:
        model = Cargo
        fields = ['nome']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Digite o nome do cargo',
        })


class LotacaoForm(forms.ModelForm):
    class Meta:
        model = Lotacao
        fields = ['nome']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Digite o nome da lotação',
        })

class FuncionarioBancariosForm(forms.ModelForm):
    class Meta:
        model = Funcionario
        fields = [
            "banco",
            "agencia",
            "tipo_conta",
            "operacao",
            "numero_conta",
            "tipo_pix",
            "pix",
        ]
        widgets = {
            "banco": forms.Select(attrs={"class": "form-select"}),
            "agencia": forms.TextInput(attrs={"class": "form-control"}),
            "tipo_conta": forms.Select(attrs={"class": "form-select"}),
            "operacao": forms.TextInput(attrs={"class": "form-control"}),
            "numero_conta": forms.TextInput(attrs={"class": "form-control"}),
            "tipo_pix": forms.Select(attrs={"class": "form-select"}),
            "pix": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "banco" in self.fields:
            self.fields["banco"].widget.attrs["class"] = "form-select"

class FuncionarioOutrosForm(forms.ModelForm):
    class Meta:
        model = Funcionario
        fields = [
            "e_social",
            "analfabeto",
            "observacoes",
        ]
        widgets = {
            "e_social": forms.TextInput(attrs={"class": "form-control"}),
            "analfabeto": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

class AnexoAvulsoFuncionarioForm(BaseStyledModelForm):
    class Meta:
        model = AnexoAvulsoFuncionario
        fields = ['titulo', 'data_documento', 'descricao', 'arquivo']
        widgets = {
            'data_documento': DateInput(),
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()

class LembreteRHForm(BaseStyledModelForm):
    class Meta:
        model = LembreteRH
        fields = [
            'funcionario',
            'titulo',
            'descricao',
            'tipo',
            'data',
            'cor',
            'concluido',
        ]
        widgets = {
            'data': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        empresa_ativa = kwargs.pop('empresa_ativa', None)
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()

        if empresa_ativa:
            self.fields['funcionario'].queryset = Funcionario.objects.filter(
                empresa=empresa_ativa
            ).order_by('nome')
        else:
            self.fields['funcionario'].queryset = Funcionario.objects.none()

class FuncionarioCadastroRapidoForm(BaseStyledModelForm):
    class Meta:
        model = Funcionario
        fields = ['nome', 'cpf']
        widgets = {
            'nome': forms.TextInput(attrs={
                'placeholder': 'Nome completo do funcionário',
            }),
            'cpf': forms.TextInput(attrs={
                'placeholder': 'CPF',
            }),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop('empresa_ativa', None)
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()

        self.fields['nome'].required = True
        self.fields['cpf'].required = True