from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError

from local.models import Local
from obras.scope import ObraEmpresaChoiceField, obras_ativas_queryset, obras_queryset
from rh.models import Funcionario

from .funcionarios_scope import (
    EstoqueFuncionarioChoiceField,
    funcionarios_estoque_queryset,
)
from .models import (
    Cautela,
    Entrega_Cautela,
    MotivoDevolucaoCautela,
    SituacaoFerramentasPosDevolucao,
)


class CautelaStaffEditForm(forms.ModelForm):
    """Edição administrativa (is_staff): inclui situação e andamento da entrega."""

    funcionario = EstoqueFuncionarioChoiceField(
        queryset=Funcionario.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select rounded-3'}),
        label='Funcionário',
    )
    obra = ObraEmpresaChoiceField(
        queryset=obras_queryset(None, None),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select rounded-3'}),
        label='Obra',
    )

    class Meta:
        model = Cautela
        fields = (
            'funcionario',
            'data_inicio_cautela',
            'data_fim',
            'local',
            'obra',
            'situacao',
            'entrega',
            'observacoes',
        )
        widgets = {
            'funcionario': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'data_inicio_cautela': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-control rounded-3', 'type': 'date'},
            ),
            'data_fim': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-control rounded-3', 'type': 'date'},
            ),
            'local': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'obra': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'situacao': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'entrega': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'observacoes': forms.Textarea(
                attrs={'class': 'form-control rounded-3', 'rows': 3}
            ),
        }
        labels = {
            'funcionario': 'Funcionário',
            'data_inicio_cautela': 'Data de início',
            'data_fim': 'Previsão / data fim',
            'local': 'Local',
            'obra': 'Obra',
            'situacao': 'Situação',
            'entrega': 'Entrega (andamento)',
            'observacoes': 'Observações',
        }

    def __init__(self, *args, empresa=None, request=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        self.fields['funcionario'].empresa_ativa = empresa
        # HTML5 type="date" só exibe valor em ISO; sem format/input_formats o Django
        # formata com DATE_INPUT_FORMATS (ex.: dd/mm/yyyy) e o campo aparece vazio.
        _date_in = ['%Y-%m-%d', '%d/%m/%Y']
        self.fields['data_inicio_cautela'].input_formats = _date_in
        self.fields['data_fim'].input_formats = _date_in
        if empresa:
            self.fields['funcionario'].queryset = funcionarios_estoque_queryset(
                request,
                empresa,
                somente_ativos=False,
            )
            self.fields['local'].queryset = Local.objects.filter(
                empresa=empresa
            ).order_by('nome')
            self.fields['local'].required = False
            self.fields['obra'].empresa_ativa = empresa
            self.fields['obra'].queryset = obras_queryset(request, empresa).order_by('nome')
            self.fields['obra'].required = False

    def clean(self):
        cleaned = super().clean()
        di = cleaned.get('data_inicio_cautela')
        df = cleaned.get('data_fim')
        if di and df and df < di:
            raise ValidationError(
                'A data fim não pode ser anterior à data de início.'
            )
        return cleaned


class CautelaForm(forms.ModelForm):
    funcionario = EstoqueFuncionarioChoiceField(
        queryset=Funcionario.objects.none(),
        widget=forms.HiddenInput(),
        label='Funcionário solicitante',
    )
    obra = ObraEmpresaChoiceField(
        queryset=obras_queryset(None, None),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select rounded-3'}),
        label='Obra',
    )

    class Meta:
        model = Cautela
        fields = (
            'funcionario',
            'data_inicio_cautela',
            'data_fim',
            'local',
            'obra',
            'observacoes',
        )
        widgets = {
            'funcionario': forms.HiddenInput(),
            'data_inicio_cautela': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-control rounded-3', 'type': 'date'},
            ),
            'data_fim': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-control rounded-3', 'type': 'date'},
            ),
            'local': forms.HiddenInput(),
            'obra': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'observacoes': forms.Textarea(
                attrs={'class': 'form-control rounded-3', 'rows': 3}
            ),
        }
        labels = {
            'funcionario': 'Funcionário solicitante',
            'data_inicio_cautela': 'Data de início',
            'data_fim': 'Previsão de entrega',
            'local': 'Local',
            'obra': 'Obra',
            'observacoes': 'Obs.',
        }

    def __init__(self, *args, empresa=None, request=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        self.fields['funcionario'].empresa_ativa = empresa

        _date_in = ['%Y-%m-%d', '%d/%m/%Y']
        self.fields['data_inicio_cautela'].input_formats = _date_in
        self.fields['data_fim'].input_formats = _date_in

        if empresa:
            self.fields['funcionario'].queryset = funcionarios_estoque_queryset(
                request,
                empresa,
            )

            self.fields['local'].queryset = Local.objects.filter(empresa=empresa).order_by(
                'nome'
            )
            # Considera "ativa" igual ao padrão do módulo de requisições.
            qs_obras = obras_ativas_queryset(request, empresa)
            self.fields['obra'].empresa_ativa = empresa
            self.fields['obra'].queryset = qs_obras.order_by('nome')

    def clean(self):
        cleaned = super().clean()
        di = cleaned.get('data_inicio_cautela')
        df = cleaned.get('data_fim')
        if di and df and df < di:
            raise ValidationError(
                'A previsão de entrega não pode ser anterior à data de início.'
            )
        return cleaned


class Entrega_CautelaForm(forms.ModelForm):
    class Meta:
        model = Entrega_Cautela
        fields = ('tipo', 'data_entrega', 'observacoes')
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'data_entrega': forms.DateInput(
                attrs={'class': 'form-control rounded-3', 'type': 'date'}
            ),
            'observacoes': forms.Textarea(
                attrs={'class': 'form-control rounded-3', 'rows': 3}
            ),
        }
        labels = {
            'tipo': 'Tipo',
            'data_entrega': 'Data da entrega',
            'observacoes': 'Obs.',
        }


class EntregaCautelaDevolucaoForm(forms.ModelForm):
    class Meta:
        model = Entrega_Cautela
        fields = (
            'data_entrega',
            'observacoes',
            'motivo',
            'situacao_ferramentas',
        )
        widgets = {
            'data_entrega': forms.DateInput(
                attrs={'class': 'form-control rounded-3', 'type': 'date'}
            ),
            'observacoes': forms.Textarea(
                attrs={'class': 'form-control rounded-3', 'rows': 3}
            ),
            'motivo': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'situacao_ferramentas': forms.Select(
                attrs={'class': 'form-select rounded-3'}
            ),
        }
        labels = {
            'data_entrega': 'Data de devolução',
            'observacoes': 'Observações',
            'motivo': 'Motivo',
            'situacao_ferramentas': 'Situação da(s) ferramentas',
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['motivo'].queryset = MotivoDevolucaoCautela.objects.filter(
                empresa=empresa, ativo=True
            ).order_by('nome')
            self.fields['situacao_ferramentas'].queryset = (
                SituacaoFerramentasPosDevolucao.objects.filter(
                    empresa=empresa, ativo=True
                ).order_by('nome')
            )
        self.fields['motivo'].required = True
        self.fields['situacao_ferramentas'].required = True

