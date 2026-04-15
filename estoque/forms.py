from django import forms
from fornecedores.models import Fornecedor

from .models import (
    CategoriaFerramenta,
    CategoriaItem,
    Ferramenta,
    Item,
    UnidadeMedida,
)


class CategoriaItemForm(forms.ModelForm):
    class Meta:
        model = CategoriaItem
        fields = ('nome',)
        widgets = {
            'nome': forms.TextInput(
                attrs={'class': 'form-control rounded-3', 'maxlength': 120}
            ),
        }
        labels = {'nome': 'Nome da categoria'}

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)

    def clean_nome(self):
        nome = (self.cleaned_data.get('nome') or '').strip()
        if not nome:
            raise forms.ValidationError('Informe o nome.')
        if self.empresa:
            qs = CategoriaItem.objects.filter(empresa=self.empresa, nome__iexact=nome)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Já existe uma categoria com este nome.')
        return nome

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.empresa and not obj.pk:
            obj.empresa = self.empresa
        if commit:
            obj.save()
        return obj


class CategoriaFerramentaForm(forms.ModelForm):
    class Meta:
        model = CategoriaFerramenta
        fields = ('nome',)
        widgets = {
            'nome': forms.TextInput(
                attrs={'class': 'form-control rounded-3', 'maxlength': 120}
            ),
        }
        labels = {'nome': 'Nome da categoria'}

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)

    def clean_nome(self):
        nome = (self.cleaned_data.get('nome') or '').strip()
        if not nome:
            raise forms.ValidationError('Informe o nome.')
        if self.empresa:
            qs = CategoriaFerramenta.objects.filter(empresa=self.empresa, nome__iexact=nome)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Já existe uma categoria com este nome.')
        return nome

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.empresa and not obj.pk:
            obj.empresa = self.empresa
        if commit:
            obj.save()
        return obj


class UnidadeMedidaForm(forms.ModelForm):
    class Meta:
        model = UnidadeMedida
        fields = ('abreviada', 'completa')
        widgets = {
            'abreviada': forms.TextInput(
                attrs={
                    'class': 'form-control rounded-3',
                    'maxlength': 32,
                    'placeholder': 'Ex.: Kg',
                }
            ),
            'completa': forms.TextInput(
                attrs={
                    'class': 'form-control rounded-3',
                    'maxlength': 120,
                    'placeholder': 'Ex.: Quilo',
                }
            ),
        }
        labels = {
            'abreviada': 'Medida abreviada',
            'completa': 'Medida completa',
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)

    def clean_abreviada(self):
        abrev = (self.cleaned_data.get('abreviada') or '').strip()
        if not abrev:
            raise forms.ValidationError('Informe a medida abreviada.')
        if self.empresa:
            qs = UnidadeMedida.objects.filter(empresa=self.empresa, abreviada__iexact=abrev)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Já existe uma unidade com esta abreviação.')
        return abrev

    def clean_completa(self):
        comp = (self.cleaned_data.get('completa') or '').strip()
        if not comp:
            raise forms.ValidationError('Informe a medida completa.')
        return comp

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.empresa and not obj.pk:
            obj.empresa = self.empresa
        if commit:
            obj.save()
        return obj


class FerramentaForm(forms.ModelForm):
    class Meta:
        model = Ferramenta
        fields = (
            'descricao',
            'marca',
            'categoria',
            'cor',
            'tamanho',
            'codigo_numeracao',
            'preco',
            'fornecedor',
            'ativo',
            'qrcode_imagem',
            'observacoes',
        )
        widgets = {
            'descricao': forms.Textarea(
                attrs={
                    'class': 'form-control rounded-3',
                    'rows': 3,
                    'maxlength': 500,
                }
            ),
            'marca': forms.TextInput(
                attrs={'class': 'form-control rounded-3', 'maxlength': 120}
            ),
            'categoria': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'cor': forms.TextInput(
                attrs={'class': 'form-control rounded-3', 'maxlength': 64}
            ),
            'tamanho': forms.TextInput(
                attrs={'class': 'form-control rounded-3', 'maxlength': 64}
            ),
            'codigo_numeracao': forms.TextInput(
                attrs={'class': 'form-control rounded-3', 'maxlength': 64}
            ),
            'preco': forms.NumberInput(
                attrs={'class': 'form-control rounded-3', 'step': '0.01', 'min': 0}
            ),
            'fornecedor': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'ativo': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input rounded-3',
                    'form': 'estoque-ferramenta-modal-form',
                }
            ),
            'qrcode_imagem': forms.ClearableFileInput(
                attrs={
                    'class': 'form-control rounded-3',
                    'accept': 'image/*',
                }
            ),
            'observacoes': forms.Textarea(
                attrs={
                    'class': 'form-control rounded-3',
                    'rows': 3,
                }
            ),
        }
        labels = {
            'descricao': 'Descrição',
            'marca': 'Marca',
            'categoria': 'Categoria',
            'cor': 'Cor',
            'tamanho': 'Tamanho',
            'codigo_numeracao': 'Código / numeração',
            'preco': 'Preço',
            'fornecedor': 'Fornecedor',
            'ativo': 'Ativa',
            'qrcode_imagem': 'QR Code',
            'observacoes': 'Obs.',
        }
        help_texts = {
            'ativo': 'Desmarque para inativar: some das buscas principais.',
            'qrcode_imagem': 'Imagem do QR Code gerada automaticamente ao salvar a ferramenta.',
        }

    def __init__(
        self,
        *args,
        empresa=None,
        lock_qrcode_imagem: bool = False,
        **kwargs,
    ):
        self.empresa = empresa
        self.lock_qrcode_imagem = bool(lock_qrcode_imagem)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['categoria'].queryset = CategoriaFerramenta.objects.filter(
                empresa=empresa
            ).order_by('nome')
            self.fields['fornecedor'].queryset = Fornecedor.objects.filter(
                empresa=empresa
            ).order_by('nome')
        self.fields['fornecedor'].required = False
        self.fields['marca'].required = False
        self.fields['cor'].required = False
        self.fields['tamanho'].required = False
        self.fields['codigo_numeracao'].required = False
        self.fields['preco'].required = False
        self.fields['qrcode_imagem'].required = False
        self.fields['observacoes'].required = False
        if self.lock_qrcode_imagem:
            self.fields['qrcode_imagem'].disabled = True

    def clean_codigo_numeracao(self):
        cod = (self.cleaned_data.get('codigo_numeracao') or '').strip()
        if not cod:
            return ''
        if self.empresa:
            qs = Ferramenta.objects.filter(
                empresa=self.empresa, codigo_numeracao__iexact=cod
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    'Já existe uma ferramenta com este código nesta empresa.'
                )
        return cod

    def clean_descricao(self):
        d = (self.cleaned_data.get('descricao') or '').strip()
        if not d:
            raise forms.ValidationError('Informe a descrição.')
        return d

    def clean(self):
        cleaned = super().clean()
        empresa = self.empresa
        if not empresa:
            return cleaned
        cat = cleaned.get('categoria')
        fr = cleaned.get('fornecedor')
        if cat and cat.empresa_id != empresa.pk:
            self.add_error('categoria', 'Categoria inválida para esta empresa.')
        if fr and fr.empresa_id != empresa.pk:
            self.add_error('fornecedor', 'Fornecedor inválido para esta empresa.')
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.empresa and not obj.pk:
            obj.empresa = self.empresa
        if commit:
            obj.save()
        return obj


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = (
            'descricao',
            'marca',
            'categoria',
            'peso',
            'unidade_medida',
            'preco',
            'fornecedor',
            'quantidade_minima',
            'quantidade_estoque',
            'ativo',
            'qrcode_imagem',
        )
        widgets = {
            'descricao': forms.Textarea(
                attrs={
                    'class': 'form-control rounded-3',
                    'rows': 3,
                    'maxlength': 500,
                }
            ),
            'marca': forms.TextInput(
                attrs={'class': 'form-control rounded-3', 'maxlength': 120}
            ),
            'categoria': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'peso': forms.NumberInput(
                attrs={'class': 'form-control rounded-3', 'step': 'any', 'min': 0}
            ),
            'unidade_medida': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'preco': forms.NumberInput(
                attrs={'class': 'form-control rounded-3', 'step': '0.01', 'min': 0}
            ),
            'fornecedor': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'quantidade_minima': forms.NumberInput(
                attrs={'class': 'form-control rounded-3', 'step': 'any', 'min': 0}
            ),
            'quantidade_estoque': forms.NumberInput(
                attrs={'class': 'form-control rounded-3', 'step': 'any', 'min': 0}
            ),
            'ativo': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input rounded-3',
                    # Permite renderizar o switch fora do <form> (header do modal)
                    # sem perder o submit do campo.
                    'form': 'estoque-item-modal-form',
                }
            ),
            'qrcode_imagem': forms.ClearableFileInput(
                attrs={
                    'class': 'form-control rounded-3',
                    'accept': 'image/*',
                }
            ),
        }
        labels = {
            'descricao': 'Descrição',
            'marca': 'Marca',
            'categoria': 'Categoria',
            'peso': 'Peso',
            'unidade_medida': 'Und. de medida',
            'preco': 'Preço',
            'fornecedor': 'Fornecedor',
            'quantidade_minima': 'Quant. mínima',
            'quantidade_estoque': 'Quant. em estoque',
            'ativo': 'Ativo',
            'qrcode_imagem': 'QR Code',
        }
        help_texts = {
            'quantidade_minima': 'Quantidade mínima no estoque (alertas futuros).',
            'quantidade_estoque': 'Saldo atual. Movimentações futuras atualizarão este campo.',
            'ativo': 'Desmarque para inativar: some das buscas operacionais e da movimentação.',
            'qrcode_imagem': 'Imagem do QR Code gerada automaticamente ao salvar o item.',
            'peso': 'Opcional. Ex.: peso por unidade.',
        }

    def __init__(
        self,
        *args,
        empresa=None,
        lock_quantidade_estoque: bool = False,
        lock_qrcode_imagem: bool = False,
        **kwargs,
    ):
        self.empresa = empresa
        self.lock_quantidade_estoque = bool(lock_quantidade_estoque)
        self.lock_qrcode_imagem = bool(lock_qrcode_imagem)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['categoria'].queryset = CategoriaItem.objects.filter(
                empresa=empresa
            ).order_by('nome')
            self.fields['unidade_medida'].queryset = UnidadeMedida.objects.filter(
                empresa=empresa
            ).order_by('abreviada')
            self.fields['fornecedor'].queryset = Fornecedor.objects.filter(
                empresa=empresa
            ).order_by('nome')
        self.fields['fornecedor'].required = False
        self.fields['marca'].required = False
        self.fields['peso'].required = False
        self.fields['preco'].required = False
        self.fields['qrcode_imagem'].required = False
        self.fields['quantidade_minima'].required = False
        self.fields['quantidade_estoque'].required = False
        if self.lock_quantidade_estoque:
            self.fields['quantidade_estoque'].disabled = True
        if self.lock_qrcode_imagem:
            self.fields['qrcode_imagem'].disabled = True

    def clean_quantidade_minima(self):
        val = self.cleaned_data.get('quantidade_minima')
        if val is None:
            return 0
        return val

    def clean_quantidade_estoque(self):
        if getattr(self, 'lock_quantidade_estoque', False):
            # Campo travado: mantém valor atual (somente Movimentar altera).
            if self.instance and getattr(self.instance, 'pk', None):
                return self.instance.quantidade_estoque
            return 0
        val = self.cleaned_data.get('quantidade_estoque')
        if val is None:
            return 0
        if val < 0:
            raise forms.ValidationError('A quantidade em estoque não pode ser negativa.')
        return val

    def clean_descricao(self):
        d = (self.cleaned_data.get('descricao') or '').strip()
        if not d:
            raise forms.ValidationError('Informe a descrição.')
        return d

    def clean(self):
        cleaned = super().clean()
        empresa = self.empresa
        if not empresa:
            return cleaned
        cat = cleaned.get('categoria')
        um = cleaned.get('unidade_medida')
        fr = cleaned.get('fornecedor')
        if cat and cat.empresa_id != empresa.pk:
            self.add_error('categoria', 'Categoria inválida para esta empresa.')
        if um and um.empresa_id != empresa.pk:
            self.add_error('unidade_medida', 'Unidade de medida inválida para esta empresa.')
        if fr and fr.empresa_id != empresa.pk:
            self.add_error('fornecedor', 'Fornecedor inválido para esta empresa.')
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.empresa and not obj.pk:
            obj.empresa = self.empresa
        if commit:
            obj.save()
        return obj
