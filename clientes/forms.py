from django import forms
from django.core.exceptions import ValidationError

from fornecedores.utils_doc import display_cpf, display_cnpj

from .models import Cliente


class CpfCnpjDisplayInput(forms.TextInput):
    """Exibe CPF/CNPJ mascarado a partir dos dígitos gravados no modelo."""

    def format_value(self, value):
        if value is None or value == '':
            return ''
        d = ''.join(c for c in str(value) if c.isdigit())
        if len(d) <= 11:
            return display_cpf(d)
        return display_cnpj(d)


class ClienteForm(forms.ModelForm):
    cpf_cnpj = forms.CharField(
        label='CPF/CNPJ',
        max_length=18,
        required=True,
        widget=CpfCnpjDisplayInput(
            attrs={
                'class': 'form-control rounded-3',
                'id': 'id_cliente_cpf_cnpj',
                'autocomplete': 'off',
            }
        ),
    )

    class Meta:
        model = Cliente
        fields = (
            'tipo',
            'cpf_cnpj',
            'nome',
            'razao_social',
            'endereco',
            'telefone',
            'email',
        )
        widgets = {
            'tipo': forms.Select(
                attrs={'class': 'form-select rounded-3', 'id': 'id_cliente_tipo'}
            ),
            'nome': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'razao_social': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'endereco': forms.Textarea(
                attrs={'class': 'form-control rounded-3', 'rows': 2}
            ),
            'telefone': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'email': forms.EmailInput(attrs={'class': 'form-control rounded-3'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        self.fields['razao_social'].required = False
        if self.data:
            tipo = (self.data.get('tipo') or 'PJ').upper()
        else:
            tipo = (getattr(self.instance, 'tipo', None) or 'PJ').upper()
        pf = tipo == 'PF'
        self.fields['cpf_cnpj'].widget.attrs['data-mask'] = 'cpf' if pf else 'cnpj'
        self.fields['cpf_cnpj'].label = 'CPF' if pf else 'CNPJ'

    def clean_cpf_cnpj(self):
        raw = self.cleaned_data.get('cpf_cnpj') or ''
        digits = ''.join(c for c in raw if c.isdigit())
        tipo = (self.cleaned_data.get('tipo') or 'PJ').upper()
        if tipo == 'PF':
            if len(digits) != 11:
                raise ValidationError('CPF deve ter 11 dígitos.')
        else:
            if len(digits) != 14:
                raise ValidationError('CNPJ deve ter 14 dígitos.')
        empresa = self.empresa
        if empresa:
            qs = Cliente.objects.filter(empresa=empresa, cpf_cnpj=digits)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    'Já existe um cliente com este CPF/CNPJ nesta empresa.'
                )
        return digits

    def clean(self):
        data = super().clean()
        tipo = data.get('tipo')
        razao = (data.get('razao_social') or '').strip()
        if tipo in ('PJ', 'AP') and not razao:
            self.add_error(
                'razao_social',
                'Informe a razão social para Pessoa Jurídica ou Administração Pública.',
            )
        return data
