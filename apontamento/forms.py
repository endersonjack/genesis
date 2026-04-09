from datetime import date

from django import forms

from local.models import Local

from .models import ApontamentoFalta, ApontamentoObservacaoLocal


class ApontamentoFaltaForm(forms.ModelForm):
    class Meta:
        model = ApontamentoFalta
        fields = ('funcionario', 'data', 'motivo', 'observacao')
        widgets = {
            'funcionario': forms.HiddenInput(),
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'motivo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Motivo'}),
            'observacao': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observação (opcional)'}
            ),
        }

    def __init__(self, *args, empresa_ativa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data'].initial = date.today()
        if empresa_ativa is not None:
            self._empresa_ativa = empresa_ativa

    def clean_funcionario(self):
        funcionario = self.cleaned_data.get('funcionario')
        empresa = getattr(self, '_empresa_ativa', None)
        if empresa and funcionario and funcionario.empresa_id != empresa.id:
            raise forms.ValidationError('Funcionário inválido para esta empresa.')
        return funcionario


class ApontamentoObservacaoLocalForm(forms.ModelForm):
    class Meta:
        model = ApontamentoObservacaoLocal
        fields = ('local', 'data', 'texto')
        widgets = {
            'local': forms.Select(attrs={'class': 'form-select'}),
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'texto': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descreva a observação'}
            ),
        }

    def __init__(self, *args, empresa_ativa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data'].initial = date.today()
        if empresa_ativa is not None:
            self.fields['local'].queryset = Local.objects.filter(empresa=empresa_ativa).order_by(
                'nome'
            )
