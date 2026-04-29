from django import forms
from django.core.exceptions import ValidationError

from rh.models import Banco

from .models import CategoriaFornecedor, Fornecedor
from .utils_doc import display_cpf, display_cnpj


class CpfCnpjDisplayInput(forms.TextInput):
    """Exibe CPF/CNPJ mascarado a partir dos dígitos gravados no modelo."""

    def format_value(self, value):
        if value is None or value == '':
            return ''
        d = ''.join(c for c in str(value) if c.isdigit())
        if len(d) <= 11:
            return display_cpf(d)
        return display_cnpj(d)


class FornecedorForm(forms.ModelForm):
    # max_length do modelo é 14 (só dígitos). No POST vem com máscara (CPF 14 ou CNPJ 18 caracteres).
    cpf_cnpj = forms.CharField(
        label='CPF/CNPJ',
        max_length=18,
        required=True,
        widget=CpfCnpjDisplayInput(
            attrs={
                'class': 'form-control rounded-3',
                'id': 'id_fornecedor_cpf_cnpj',
                'autocomplete': 'off',
            }
        ),
    )

    class Meta:
        model = Fornecedor
        fields = (
            'tipo',
            'categoria',
            'cpf_cnpj',
            'nome',
            'razao_social',
            'endereco',
            'telefone_loja',
            'telefone_financeiro',
            'contato_financeiro',
            'email',
            'banco',
            'agencia',
            'tipo_conta',
            'operacao',
            'numero_conta',
            'tipo_pix',
            'pix',
        )
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select rounded-3', 'id': 'id_fornecedor_tipo'}),
            'categoria': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'nome': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'razao_social': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'endereco': forms.Textarea(
                attrs={'class': 'form-control rounded-3', 'rows': 2}
            ),
            'telefone_loja': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'telefone_financeiro': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'contato_financeiro': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'email': forms.EmailInput(attrs={'class': 'form-control rounded-3'}),
            'banco': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'agencia': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'tipo_conta': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'operacao': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'numero_conta': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'tipo_pix': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'pix': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['categoria'].queryset = CategoriaFornecedor.objects.filter(
                empresa=empresa
            ).order_by('nome')
        self.fields['banco'].queryset = Banco.objects.order_by('nome')
        self.fields['categoria'].required = False
        self.fields['razao_social'].required = False
        if self.data:
            tipo = (self.data.get('tipo') or 'PJ').upper()
        else:
            tipo = (getattr(self.instance, 'tipo', None) or 'PJ').upper()
        mask = 'cpf' if tipo == 'PF' else 'cnpj'
        self.fields['cpf_cnpj'].widget.attrs['data-mask'] = mask
        if tipo == 'PF':
            self.fields['cpf_cnpj'].label = 'CPF'
        else:
            self.fields['cpf_cnpj'].label = 'CNPJ'

    def clean_cpf_cnpj(self):
        raw = self.cleaned_data.get('cpf_cnpj') or ''
        digits = ''.join(c for c in raw if c.isdigit())
        tipo = self.cleaned_data.get('tipo') or 'PJ'
        if tipo == 'PF':
            if len(digits) != 11:
                raise ValidationError('CPF deve ter 11 dígitos.')
        else:
            if len(digits) != 14:
                raise ValidationError('CNPJ deve ter 14 dígitos.')
        empresa = self.empresa
        if empresa:
            qs = Fornecedor.objects.filter(empresa=empresa, cpf_cnpj=digits)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Já existe um fornecedor com este CPF/CNPJ nesta empresa.')
        return digits

    def clean(self):
        data = super().clean()
        tipo = data.get('tipo')
        razao = (data.get('razao_social') or '').strip()
        if tipo == 'PJ' and not razao:
            self.add_error('razao_social', 'Informe a razão social para Pessoa Jurídica.')
        return data


class FornecedorQuickCreateForm(forms.ModelForm):
    cpf_cnpj = forms.CharField(
        label='CPF/CNPJ',
        max_length=18,
        required=True,
        widget=CpfCnpjDisplayInput(
            attrs={
                'class': 'form-control rounded-3',
                'id': 'id_fornecedor_rapido_cpf_cnpj',
                'autocomplete': 'off',
            }
        ),
    )

    class Meta:
        model = Fornecedor
        fields = ('tipo', 'cpf_cnpj', 'nome', 'razao_social')
        widgets = {
            'tipo': forms.Select(
                attrs={
                    'class': 'form-select rounded-3',
                    'id': 'id_fornecedor_rapido_tipo',
                }
            ),
            'nome': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'razao_social': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        self.fields['razao_social'].required = False
        if self.data:
            tipo = (self.data.get('tipo') or 'PJ').upper()
        else:
            tipo = (getattr(self.instance, 'tipo', None) or 'PJ').upper()
        mask = 'cpf' if tipo == 'PF' else 'cnpj'
        self.fields['cpf_cnpj'].widget.attrs['data-mask'] = mask
        self.fields['cpf_cnpj'].widget.attrs['maxlength'] = '14' if tipo == 'PF' else '18'
        self.fields['cpf_cnpj'].label = 'CPF' if tipo == 'PF' else 'CNPJ'

    def clean_cpf_cnpj(self):
        raw = self.cleaned_data.get('cpf_cnpj') or ''
        digits = ''.join(c for c in raw if c.isdigit())
        tipo = self.cleaned_data.get('tipo') or 'PJ'
        if tipo == 'PF':
            if len(digits) != 11:
                raise ValidationError('CPF deve ter 11 dígitos.')
        else:
            if len(digits) != 14:
                raise ValidationError('CNPJ deve ter 14 dígitos.')
        if self.empresa:
            qs = Fornecedor.objects.filter(empresa=self.empresa, cpf_cnpj=digits)
            if qs.exists():
                raise ValidationError('Já existe um fornecedor com este CPF/CNPJ nesta empresa.')
        return digits

    def clean(self):
        data = super().clean()
        tipo = data.get('tipo')
        razao = (data.get('razao_social') or '').strip()
        if tipo == 'PJ' and not razao:
            self.add_error('razao_social', 'Informe a razão social para Pessoa Jurídica.')
        return data

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.empresa = self.empresa
        if commit:
            obj.full_clean()
            obj.save()
        return obj
