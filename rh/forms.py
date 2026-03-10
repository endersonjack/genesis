from django import forms
from django.forms import inlineformset_factory

from .models import (
    Funcionario,
    Dependente,
    Cargo,
    Lotacao,
    TipoContrato,
    Lotacao,
)


class DateInput(forms.DateInput):
    input_type = 'date'


class FuncionarioForm(forms.ModelForm):
    class Meta:
        model = Funcionario
        fields = [
            'matricula',
            'foto',
            'nome',
            'cpf',
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
            'cargo',
            'lotacao',
            'situacao_atual',
            'data_admissao',
            'inicio_prorrogacao',
            'fim_prorrogacao',
            'tipo_contrato',
            'salario',
            'adicional',
            'data_ultimo_exame',
            'responsavel',
            'data_demissao',
            'tipo_demissao',
            'inicio_afastamento',
            'fim_afastamento',
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
            'inicio_afastamento': DateInput(),
            'fim_afastamento': DateInput(),
            'data_demissao': DateInput(),
            'data_ultimo_exame': DateInput(),
            'observacoes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        empresa_ativa = kwargs.pop('empresa_ativa', None)
        super().__init__(*args, **kwargs)

        obrigatorios = ['nome', 'cpf', 'situacao_atual', 'cargo']

        for nome, field in self.fields.items():
            field.required = nome in obrigatorios

            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, forms.ClearableFileInput):
                field.widget.attrs['class'] = 'form-control'
            else:
                css = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
                field.widget.attrs['class'] = css

        if empresa_ativa:
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


class DependenteForm(forms.ModelForm):
    class Meta:
        model = Dependente
        fields = ['nome', 'data_nascimento', 'cpf', 'parentesco']
        widgets = {
            'data_nascimento': DateInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for nome, field in self.fields.items():
            css = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs['class'] = css


DependenteFormSet = inlineformset_factory(
    Funcionario,
    Dependente,
    form=DependenteForm,
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
            'placeholder': 'Digite o nome do cargo'
        })


class LotacaoForm(forms.ModelForm):
    class Meta:
        model = Lotacao
        fields = ['nome']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Digite o nome da lotação'
        })