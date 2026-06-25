from django import forms

from .models import NotaAutoadesiva


class NotaAutoadesivaForm(forms.ModelForm):
    class Meta:
        model = NotaAutoadesiva
        fields = ['empresa', 'responsaveis', 'cor', 'anexo', 'texto']
        widgets = {
            'texto': forms.Textarea(
                attrs={
                    'rows': 3,
                    'placeholder': 'Escreva um lembrete ou tarefa...',
                }
            ),
            'cor': forms.TextInput(attrs={'type': 'color'}),
            'responsaveis': forms.SelectMultiple(attrs={'size': 5}),
        }
        labels = {
            'empresa': 'Empresa',
            'responsaveis': 'Responsáveis',
            'cor': 'Cor da nota',
            'anexo': 'Anexo',
            'texto': 'Nota',
        }

    def __init__(self, *args, empresas_qs=None, usuarios_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresas_qs is not None:
            self.fields['empresa'].queryset = empresas_qs
        if usuarios_qs is not None:
            self.fields['responsaveis'].queryset = usuarios_qs
        self.fields['responsaveis'].required = False
        self.fields['anexo'].required = False

        for field in self.fields.values():
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f'{css} form-control'.strip()
        self.fields['empresa'].widget.attrs['class'] = 'form-select'
        self.fields['responsaveis'].widget.attrs['class'] = 'form-select'
        self.fields['cor'].widget.attrs['class'] = 'form-control form-control-color'
        self.fields['cor'].widget.attrs['title'] = 'Escolha a cor da nota'

    def clean_cor(self):
        cor = (self.cleaned_data.get('cor') or '').strip()
        if len(cor) != 7 or not cor.startswith('#'):
            raise forms.ValidationError('Escolha uma cor válida.')
        try:
            int(cor[1:], 16)
        except ValueError as exc:
            raise forms.ValidationError('Escolha uma cor válida.') from exc
        return cor
