from django import forms
from .models import Empresa


class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = '__all__'
        widgets = {
            'cor_tema': forms.TextInput(attrs={'type': 'color'}),
        }


class EmpresaPreferenciasForm(forms.ModelForm):
    """Dados cadastrais e identidade visual da empresa ativa."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in (
            'razao_social',
            'nome_fantasia',
            'cnpj',
            'email',
            'telefone',
            'endereco',
        ):
            if name in self.fields:
                self.fields[name].widget.attrs.setdefault('class', 'form-control')
        if 'cor_tema' in self.fields:
            self.fields['cor_tema'].widget.attrs.setdefault('class', 'form-control form-control-color')
        if 'logo' in self.fields:
            self.fields['logo'].widget.attrs.setdefault('class', 'form-control')

    class Meta:
        model = Empresa
        fields = [
            'razao_social',
            'nome_fantasia',
            'cnpj',
            'email',
            'telefone',
            'endereco',
            'logo',
            'cor_tema',
        ]
        widgets = {
            'cor_tema': forms.TextInput(attrs={'type': 'color'}),
            'logo': forms.ClearableFileInput(
                attrs={
                    'class': 'form-control',
                    'accept': 'image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp',
                }
            ),
        }
