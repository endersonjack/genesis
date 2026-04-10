from django import forms
from django.utils import timezone

from local.models import Local

from .models import ApontamentoFalta, ApontamentoObservacaoLocal


def _hoje_para_campo_data(form: forms.ModelForm) -> None:
    """Garante data padrão em formulário novo (ModelForm preenche initial com None)."""
    if getattr(form.instance, 'pk', None):
        return
    if form.initial.get('data'):
        return
    form.initial['data'] = timezone.localdate()


def _campo_data_html5(field: forms.DateField) -> None:
    """type=date exige valor ISO; com pt-br o widget padrão usa d/m/Y e o campo fica vazio."""
    field.widget.format = '%Y-%m-%d'
    field.widget.attrs.setdefault('type', 'date')
    fmts = list(field.input_formats) if field.input_formats else []
    if '%Y-%m-%d' not in fmts:
        field.input_formats = ['%Y-%m-%d', *fmts]


class ApontamentoFaltaForm(forms.ModelForm):
    class Meta:
        model = ApontamentoFalta
        fields = ('funcionario', 'data', 'motivo', 'observacao')
        widgets = {
            'funcionario': forms.HiddenInput(),
            'data': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'form-control'},
            ),
            'motivo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Motivo'}),
            'observacao': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observação (opcional)'}
            ),
        }

    def __init__(self, *args, empresa_ativa=None, **kwargs):
        super().__init__(*args, **kwargs)
        _campo_data_html5(self.fields['data'])
        _hoje_para_campo_data(self)
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
            'data': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'form-control'},
            ),
            'texto': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descreva a observação'}
            ),
        }

    def __init__(self, *args, empresa_ativa=None, **kwargs):
        super().__init__(*args, **kwargs)
        _campo_data_html5(self.fields['data'])
        _hoje_para_campo_data(self)
        if empresa_ativa is not None:
            self.fields['local'].queryset = Local.objects.filter(empresa=empresa_ativa).order_by(
                'nome'
            )
