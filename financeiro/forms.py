"""Formulários do módulo financeiro."""
from __future__ import annotations

from decimal import Decimal

from django import forms
from django.forms import formset_factory
from django.utils import timezone

from clientes.models import Cliente
from core.moeda_fmt import format_decimal_br_moeda, parse_valor_moeda_obrigatorio
from estoque.models import UnidadeMedida
from fornecedores.models import Fornecedor
from obras.models import Obra

from .models import (
    BoletoPagamento,
    Caixa,
    CategoriaFinanceira,
    PagamentoNotaFiscal,
    PagamentoNotaFiscalItem,
    PagamentoNotaFiscalPagamento,
    RecebimentoAvulso,
    RecebimentoMedicao,
)


class RecebimentoAvulsoForm(forms.Form):
    caixa = forms.ModelChoiceField(
        label='Caixa',
        queryset=Caixa.objects.none(),
        required=True,
    )
    cliente = forms.ModelChoiceField(
        label='Cliente',
        queryset=Cliente.objects.none(),
        required=True,
    )
    categoria = forms.ModelChoiceField(
        label='Categoria',
        queryset=CategoriaFinanceira.objects.none(),
        required=False,
    )
    descricao = forms.CharField(
        label='Descrição',
        max_length=500,
        widget=forms.TextInput(attrs={'class': 'form-control rounded-3'}),
    )
    data = forms.DateField(
        label='Data',
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control rounded-3'},
        ),
    )
    valor = forms.CharField(
        label='Valor bruto (R$)',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control rounded-3 text-end js-recebimento-valor',
                'data-mask': 'br-moeda',
                'inputmode': 'decimal',
                'autocomplete': 'off',
                'maxlength': '22',
                'placeholder': '0,00',
            },
        ),
    )
    impostos = forms.CharField(
        label='Impostos (R$)',
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control rounded-3 text-end js-recebimento-impostos',
                'data-mask': 'br-moeda',
                'inputmode': 'decimal',
                'autocomplete': 'off',
                'maxlength': '22',
                'placeholder': '0,00',
            },
        ),
    )
    valor_liquido = forms.CharField(
        label='Valor líquido (R$)',
        required=False,
        disabled=True,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control rounded-3 text-end fw-bold js-recebimento-liquido',
                'data-mask': 'br-moeda',
                'inputmode': 'decimal',
                'autocomplete': 'off',
                'placeholder': '0,00',
            },
        ),
    )
    comprovante = forms.FileField(
        label='Comprovante',
        required=False,
        widget=forms.ClearableFileInput(
            attrs={'class': 'form-control rounded-3'},
        ),
    )
    observacao = forms.CharField(
        label='Observação',
        required=False,
        widget=forms.Textarea(
            attrs={'class': 'form-control rounded-3', 'rows': 3},
        ),
    )

    def __init__(self, *args, empresa=None, instance=None, **kwargs):
        self.empresa = empresa
        self.instance = instance
        super().__init__(*args, **kwargs)
        self.initial.setdefault('impostos', format_decimal_br_moeda(Decimal('0')))
        self.initial.setdefault('valor_liquido', format_decimal_br_moeda(Decimal('0')))
        if instance and not self.is_bound:
            self.initial.update(
                {
                    'caixa': instance.caixa_id,
                    'cliente': instance.cliente_id,
                    'categoria': instance.categoria_id,
                    'descricao': instance.descricao,
                    'data': instance.data.isoformat() if instance.data else '',
                    'valor': format_decimal_br_moeda(instance.valor),
                    'impostos': format_decimal_br_moeda(instance.impostos),
                    'valor_liquido': format_decimal_br_moeda(instance.valor_liquido),
                    'observacao': instance.observacao,
                }
            )
        if empresa:
            self.fields['caixa'].queryset = Caixa.objects.filter(
                empresa=empresa, ativo=True
            ).order_by('tipo', 'nome')
            self.fields['cliente'].queryset = Cliente.objects.filter(
                empresa=empresa,
            ).order_by('nome')
            self.fields['categoria'].queryset = CategoriaFinanceira.objects.filter(
                empresa=empresa,
                movimentacao_tipo=CategoriaFinanceira.MovimentacaoTipo.RECEBIMENTO_AVULSO,
                ativo=True,
            ).order_by('nome')
        for _n, f in self.fields.items():
            if isinstance(
                f.widget,
                (forms.Select, forms.SelectMultiple),
            ):
                f.widget.attrs.setdefault('class', 'form-select rounded-3')

    def clean_caixa(self):
        caixa = self.cleaned_data['caixa']
        if self.empresa and caixa.empresa_id != self.empresa.pk:
            raise forms.ValidationError('Caixa inválido para esta empresa.')
        return caixa

    def clean_cliente(self):
        cliente = self.cleaned_data['cliente']
        if self.empresa and cliente.empresa_id != self.empresa.pk:
            raise forms.ValidationError('Cliente inválido para esta empresa.')
        return cliente

    def clean_categoria(self):
        categoria = self.cleaned_data.get('categoria')
        if categoria is None:
            return categoria
        if self.empresa and categoria.empresa_id != self.empresa.pk:
            raise forms.ValidationError('Categoria inválida para esta empresa.')
        if (
            categoria.movimentacao_tipo
            != CategoriaFinanceira.MovimentacaoTipo.RECEBIMENTO_AVULSO
        ):
            raise forms.ValidationError('Selecione uma categoria de recebimento.')
        if not categoria.ativo:
            raise forms.ValidationError('Esta categoria está inativa.')
        return categoria

    def clean_valor(self):
        return parse_valor_moeda_obrigatorio(self.cleaned_data.get('valor'))

    def clean_impostos(self):
        raw = self.cleaned_data.get('impostos')
        if raw in (None, ''):
            return Decimal('0')
        return parse_valor_moeda_obrigatorio(raw)

    def clean_valor_liquido(self):
        if self.fields['valor_liquido'].disabled:
            return Decimal('0')
        return parse_valor_moeda_obrigatorio(self.cleaned_data.get('valor_liquido'))

    def clean(self):
        cleaned = super().clean()
        valor = cleaned.get('valor')
        impostos = cleaned.get('impostos') or Decimal('0')
        if valor is not None and impostos >= valor:
            self.add_error('impostos', 'Impostos devem ser menores que o valor bruto.')
        if valor is not None and self.fields['valor_liquido'].disabled:
            cleaned['valor_liquido'] = valor - impostos
        elif valor is not None and cleaned.get('valor_liquido') != valor - impostos:
            self.add_error(
                'valor_liquido',
                'Valor líquido deve ser o valor bruto menos impostos.',
            )
        return cleaned


class RecebimentoAvulsoEditForm(RecebimentoAvulsoForm):
    data_pagamento = forms.DateField(
        label='Data de pagamento/liquidação',
        required=False,
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control rounded-3'},
        ),
    )
    field_order = (
        'caixa',
        'cliente',
        'categoria',
        'descricao',
        'data',
        'data_pagamento',
        'valor',
        'impostos',
        'valor_liquido',
        'comprovante',
        'observacao',
    )

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, instance=instance, **kwargs)
        self.fields['valor_liquido'].disabled = False
        self.fields['valor_liquido'].required = True
        if instance and not self.is_bound:
            self.initial['data_pagamento'] = (
                instance.data_pagamento.isoformat() if instance.data_pagamento else ''
            )

    def clean(self):
        cleaned = super().clean()
        if (
            self.instance
            and self.instance.status == self.instance.Status.PAGO
            and not cleaned.get('data_pagamento')
        ):
            self.add_error('data_pagamento', 'Informe a data de pagamento/liquidação.')
        return cleaned


class RecebimentoLiquidacaoForm(forms.Form):
    data_pagamento = forms.DateField(
        label='Data de pagamento/liquidação',
        initial=timezone.localdate,
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control rounded-3'},
        ),
    )
    valor = forms.CharField(
        label='Valor bruto (R$)',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control rounded-3 text-end js-liquidacao-valor',
                'data-mask': 'br-moeda',
                'inputmode': 'decimal',
                'autocomplete': 'off',
                'maxlength': '22',
                'placeholder': '0,00',
            },
        ),
    )
    impostos = forms.CharField(
        label='Valor de impostos (R$)',
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control rounded-3 text-end js-liquidacao-impostos',
                'data-mask': 'br-moeda',
                'inputmode': 'decimal',
                'autocomplete': 'off',
                'maxlength': '22',
                'placeholder': '0,00',
            },
        ),
    )
    valor_liquido = forms.CharField(
        label='Valor líquido (R$)',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control rounded-3 text-end fw-bold js-liquidacao-liquido',
                'data-mask': 'br-moeda',
                'inputmode': 'decimal',
                'autocomplete': 'off',
                'maxlength': '22',
                'placeholder': '0,00',
            },
        ),
    )

    def __init__(self, *args, recebimento=None, **kwargs):
        super().__init__(*args, **kwargs)
        if recebimento and not self.is_bound:
            self.initial['data_pagamento'] = timezone.localdate().isoformat()
            self.initial['valor'] = format_decimal_br_moeda(recebimento.valor)
            self.initial['impostos'] = format_decimal_br_moeda(recebimento.impostos)
            self.initial['valor_liquido'] = format_decimal_br_moeda(recebimento.valor_liquido)

    def clean_valor(self):
        return parse_valor_moeda_obrigatorio(self.cleaned_data.get('valor'))

    def clean_impostos(self):
        raw = self.cleaned_data.get('impostos')
        if raw in (None, ''):
            return Decimal('0')
        return parse_valor_moeda_obrigatorio(raw)

    def clean_valor_liquido(self):
        return parse_valor_moeda_obrigatorio(self.cleaned_data.get('valor_liquido'))

    def clean(self):
        cleaned = super().clean()
        valor = cleaned.get('valor')
        impostos = cleaned.get('impostos') or Decimal('0')
        valor_liquido = cleaned.get('valor_liquido')
        if valor is None or valor_liquido is None:
            return cleaned
        if impostos < 0:
            self.add_error('impostos', 'Valor não pode ser negativo.')
        if valor_liquido <= 0:
            self.add_error('valor_liquido', 'Informe um valor líquido maior que zero.')
        if impostos >= valor:
            self.add_error('impostos', 'Impostos devem ser menores que o valor bruto.')
        if valor - impostos != valor_liquido:
            self.add_error(
                'valor_liquido',
                'Valor líquido deve ser o valor bruto menos impostos.',
            )
        return cleaned


class RecebimentoMedicaoForm(RecebimentoAvulsoForm):
    obra = forms.ModelChoiceField(
        label='Obra',
        queryset=Obra.objects.none(),
        required=True,
    )
    medicao_numero = forms.CharField(
        label='Medição nº',
        max_length=120,
        widget=forms.TextInput(attrs={'class': 'form-control rounded-3'}),
    )
    nota_fiscal_numero = forms.CharField(
        label='Nº nota fiscal',
        max_length=60,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control rounded-3'}),
    )
    field_order = (
        'caixa',
        'cliente',
        'categoria',
        'obra',
        'medicao_numero',
        'nota_fiscal_numero',
        'descricao',
        'data',
        'valor',
        'impostos',
        'valor_liquido',
        'comprovante',
        'observacao',
    )

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, empresa=empresa, **kwargs)
        if empresa:
            self.fields['obra'].queryset = Obra.objects.filter(empresa=empresa).order_by(
                'nome'
            )
        if self.instance and not self.is_bound:
            self.initial.update(
                {
                    'obra': self.instance.obra_id,
                    'medicao_numero': self.instance.medicao_numero,
                    'nota_fiscal_numero': self.instance.nota_fiscal_numero,
                }
            )

    def clean(self):
        cleaned = super().clean()
        if not self.empresa:
            return cleaned
        obra = cleaned.get('obra')
        cliente = cleaned.get('cliente')
        if obra and cliente and obra.contratante_id != cliente.pk:
            self.add_error(
                'obra',
                'A obra selecionada não pertence a este cliente (contratante).',
            )
        if obra and obra.empresa_id != self.empresa.pk:
            self.add_error('obra', 'Obra inválida para esta empresa.')
        return cleaned


class RecebimentoMedicaoEditForm(RecebimentoMedicaoForm):
    data_pagamento = forms.DateField(
        label='Data de pagamento/liquidação',
        required=False,
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control rounded-3'},
        ),
    )
    field_order = (
        'caixa',
        'cliente',
        'categoria',
        'obra',
        'medicao_numero',
        'nota_fiscal_numero',
        'descricao',
        'data',
        'data_pagamento',
        'valor',
        'impostos',
        'valor_liquido',
        'comprovante',
        'observacao',
    )

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, instance=instance, **kwargs)
        self.fields['valor_liquido'].disabled = False
        self.fields['valor_liquido'].required = True
        if instance and not self.is_bound:
            self.initial['data_pagamento'] = (
                instance.data_pagamento.isoformat() if instance.data_pagamento else ''
            )

    def clean(self):
        cleaned = super().clean()
        if (
            self.instance
            and self.instance.status == self.instance.Status.PAGO
            and not cleaned.get('data_pagamento')
        ):
            self.add_error('data_pagamento', 'Informe a data de pagamento/liquidação.')
        return cleaned


class CaixaNovoForm(forms.ModelForm):
    """Subcaixa (obra ou personalizada). Caixa geral é único por empresa (via admin/setup)."""

    class Meta:
        model = Caixa
        fields = ('tipo', 'nome', 'obra')
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'nome': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'obra': forms.Select(attrs={'class': 'form-select rounded-3'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        # ModelForm chama instance.full_clean() em _post_clean sem passar pelo save().
        # Sem empresa no instance, Caixa.clean() compara obra.empresa_id com empresa_id
        # ainda None e dispara erro falso.
        if empresa:
            self.instance.empresa = empresa
        allowed = {Caixa.Tipo.OBRA, Caixa.Tipo.PERSONALIZADA}
        self.fields['tipo'].choices = [
            c for c in Caixa.Tipo.choices if c[0] in allowed
        ]
        self.fields['obra'].queryset = Obra.objects.none()
        self.fields['obra'].required = False
        if empresa:
            self.fields['obra'].queryset = Obra.objects.filter(empresa=empresa).order_by(
                'nome'
            )

    def clean(self):
        cleaned = super().clean()
        if not self.empresa:
            return cleaned
        tipo = cleaned.get('tipo')
        obra = cleaned.get('obra')
        if tipo == Caixa.Tipo.OBRA:
            if not obra:
                self.add_error('obra', 'Informe a obra desta subcaixa.')
            elif obra.empresa_id != self.empresa.pk:
                self.add_error('obra', 'Obra inválida para esta empresa.')
        elif tipo == Caixa.Tipo.PERSONALIZADA and obra:
            self.add_error('obra', 'Subcaixa personalizada não usa obra.')
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.empresa = self.empresa
        if obj.tipo == Caixa.Tipo.PERSONALIZADA:
            obj.obra = None
        if commit:
            obj.full_clean()
            obj.save()
        return obj


class CaixaEditForm(forms.ModelForm):
    class Meta:
        model = Caixa
        fields = ('nome', 'obra', 'ativo')
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'obra': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        self.fields['ativo'].label = 'Ativo'
        self.fields['ativo'].help_text = (
            'Desmarque para inativar o caixa. Inativos não entram em novos lançamentos; '
            'o histórico permanece.'
        )
        inst = self.instance
        if inst and inst.pk:
            if inst.tipo in (Caixa.Tipo.GERAL, Caixa.Tipo.PERSONALIZADA):
                del self.fields['obra']
            elif inst.tipo == Caixa.Tipo.OBRA and empresa:
                self.fields['obra'].queryset = Obra.objects.filter(empresa=empresa).order_by(
                    'nome'
                )

    def clean_obra(self):
        obra = self.cleaned_data.get('obra')
        if obra is None:
            return obra
        if self.empresa and obra.empresa_id != self.empresa.pk:
            raise forms.ValidationError('Obra inválida para esta empresa.')
        return obra

    def save(self, commit=True):
        obj = super().save(commit=False)
        if commit:
            obj.full_clean()
            obj.save()
        return obj


class CategoriaFinanceiraForm(forms.ModelForm):
    class Meta:
        model = CategoriaFinanceira
        fields = ('nome', 'movimentacao_tipo', 'ativo')
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'movimentacao_tipo': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        self.fields['ativo'].label = 'Ativo'
        self.fields['ativo'].help_text = (
            'Desmarque para inativar. Categorias inativas não devem aparecer '
            'em novos lançamentos; o histórico permanece.'
        )
        self.fields['movimentacao_tipo'].label = 'Tipo de movimentação'
        self.fields['movimentacao_tipo'].help_text = (
            'Define em quais lançamentos esta categoria aparece para seleção.'
        )

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.empresa:
            obj.empresa = self.empresa
        obj.tipo = CategoriaFinanceira.tipo_from_movimentacao(obj.movimentacao_tipo)
        if commit:
            obj.full_clean()
            obj.save()
        return obj


class PagamentoNotaFiscalForm(forms.ModelForm):
    class Meta:
        model = PagamentoNotaFiscal
        fields = ('fornecedor', 'numero_nf', 'data_emissao', 'caixa', 'descricao')
        widgets = {
            'fornecedor': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'numero_nf': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'data_emissao': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'form-control rounded-3'},
            ),
            'caixa': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        if 'descricao' in self.fields:
            self.fields['descricao'].required = False
        if not self.is_bound and not self.initial.get('data_emissao'):
            # input type="date" exige YYYY-MM-DD para preencher no browser
            self.initial['data_emissao'] = timezone.localdate().isoformat()
        if empresa:
            self.fields['fornecedor'].queryset = Fornecedor.objects.filter(
                empresa=empresa
            ).order_by('nome')
            self.fields['caixa'].queryset = Caixa.objects.filter(
                empresa=empresa,
                ativo=True,
            ).order_by('tipo', 'nome')
            if not self.is_bound and not self.initial.get('caixa'):
                caixa_geral = (
                    Caixa.objects.filter(
                        empresa=empresa,
                        tipo=Caixa.Tipo.GERAL,
                    )
                    .order_by('pk')
                    .first()
                )
                if caixa_geral:
                    self.initial['caixa'] = caixa_geral.pk

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.empresa:
            obj.empresa = self.empresa
        if commit:
            obj.full_clean()
            obj.save()
        return obj


class PagamentoNotaFiscalItemForm(forms.ModelForm):
    unidade = forms.ChoiceField(
        label='Unidade',
        required=False,
        choices=(),
        widget=forms.Select(attrs={'class': 'form-select rounded-3'}),
    )
    valor_unitario = forms.CharField(
        label='Valor unitário (R$)',
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control rounded-3 text-end',
                'data-mask': 'br-moeda',
                'inputmode': 'decimal',
                'autocomplete': 'off',
                'maxlength': '22',
                'placeholder': '0,00',
            }
        ),
    )
    valor_total = forms.CharField(
        label='Valor total (R$)',
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control rounded-3 text-end bg-light',
                'data-mask': 'br-moeda',
                'inputmode': 'decimal',
                'autocomplete': 'off',
                'maxlength': '22',
                'placeholder': '0,00',
                'readonly': 'readonly',
            }
        ),
    )

    class Meta:
        model = PagamentoNotaFiscalItem
        fields = (
            'tipo',
            'descricao',
            'categoria',
            'quantidade',
            'unidade',
            'valor_unitario',
            'valor_total',
            'caixa',
        )
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'categoria': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'quantidade': forms.NumberInput(
                attrs={'class': 'form-control rounded-3', 'step': '0.0001', 'min': '0'}
            ),
            'caixa': forms.Select(attrs={'class': 'form-select rounded-3'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        default_caixa_id = kwargs.pop('default_caixa_id', None)
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        for field_name in (
            'tipo',
            'descricao',
            'categoria',
            'quantidade',
            'unidade',
            'valor_unitario',
            'valor_total',
            'caixa',
        ):
            if field_name in self.fields:
                self.fields[field_name].required = False
        if empresa:
            unidade_choices = [('', '---------')] + [
                (unidade.abreviada, unidade.abreviada)
                for unidade in UnidadeMedida.objects.filter(empresa=empresa).order_by(
                    'abreviada'
                )
            ]
            self.fields['categoria'].queryset = CategoriaFinanceira.objects.filter(
                empresa=empresa,
                movimentacao_tipo=CategoriaFinanceira.MovimentacaoTipo.PAGAMENTO_NOTA_FISCAL,
            ).order_by('nome')
            self.fields['unidade'].choices = unidade_choices
            self.fields['caixa'].queryset = Caixa.objects.filter(
                empresa=empresa,
                ativo=True,
            ).order_by('tipo', 'nome')
            if not self.is_bound:
                if not self.initial.get('tipo'):
                    self.initial['tipo'] = PagamentoNotaFiscalItem.TipoItem.PRODUTO
                if not self.initial.get('unidade'):
                    unidade_values = [value for value, _label in unidade_choices]
                    if 'UND' in unidade_values:
                        self.initial['unidade'] = 'UND'
                if default_caixa_id and not self.initial.get('caixa'):
                    self.initial['caixa'] = default_caixa_id
        if self.instance and self.instance.pk:
            self.initial['valor_unitario'] = format_decimal_br_moeda(
                self.instance.valor_unitario
            )
            self.initial['valor_total'] = format_decimal_br_moeda(self.instance.valor_total)

    def _raw_value(self, field_name: str) -> str:
        if not self.is_bound:
            return ''
        return str(self.data.get(self.add_prefix(field_name), '')).strip()

    def _linha_vazia(self) -> bool:
        tipo = self._raw_value('tipo')
        descricao = self._raw_value('descricao')
        categoria = self._raw_value('categoria')
        quantidade = self._raw_value('quantidade')
        unidade = self._raw_value('unidade')
        caixa = self._raw_value('caixa')
        valor_unitario = self._raw_value('valor_unitario')
        valor_total = self._raw_value('valor_total')
        zeros = ('', '0', '0,0', '0,00', '0.00', '0,0000')

        # A linha extra do formset pode vir com defaults como tipo, quantidade=1 e caixa já
        # selecionado. So consideramos a linha "preenchida" quando há informação material.
        return (
            descricao == ''
            and categoria == ''
            and unidade == ''
            and valor_unitario in zeros
            and valor_total in zeros
            and quantidade in ('', '1', '1,0', '1,00', '1.00', '1,0000', '1.0000')
            and tipo in ('', PagamentoNotaFiscalItem.TipoItem.PRODUTO)
            and caixa != '__force_not_empty__'
        )

    def clean_valor_unitario(self):
        raw = self.cleaned_data.get('valor_unitario')
        if self._linha_vazia() and raw in (None, '', '0', '0,0', '0,00'):
            return Decimal('0')
        return parse_valor_moeda_obrigatorio(raw)

    def clean_valor_total(self):
        raw = self.cleaned_data.get('valor_total')
        if self._linha_vazia() and raw in (None, '', '0', '0,0', '0,00'):
            return Decimal('0')
        return parse_valor_moeda_obrigatorio(raw)

    def clean(self):
        cleaned_data = super().clean()
        if self._linha_vazia():
            cleaned_data['_skip_form'] = True
            return cleaned_data

        if not cleaned_data.get('tipo'):
            self.add_error('tipo', 'Este campo é obrigatório.')
        if not cleaned_data.get('descricao'):
            self.add_error('descricao', 'Este campo é obrigatório.')
        if cleaned_data.get('quantidade') in (None, ''):
            self.add_error('quantidade', 'Este campo é obrigatório.')
        elif cleaned_data['quantidade'] <= 0:
            self.add_error('quantidade', 'Informe uma quantidade maior que zero.')
        if not cleaned_data.get('caixa'):
            self.add_error('caixa', 'Este campo é obrigatório.')
        if cleaned_data.get('valor_unitario') in (None, Decimal('0')):
            self.add_error('valor_unitario', 'Este campo é obrigatório.')
        if cleaned_data.get('valor_total') in (None, Decimal('0')):
            self.add_error('valor_total', 'Informe um valor maior que zero.')
        return cleaned_data

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.valor_unitario = self.cleaned_data['valor_unitario']
        obj.valor_total = self.cleaned_data['valor_total']
        if commit:
            obj.full_clean()
            obj.save()
        return obj


PagamentoNotaFiscalItemFormSet = formset_factory(
    PagamentoNotaFiscalItemForm,
    extra=1,
    can_delete=True,
)

PagamentoNotaFiscalItemEditFormSet = formset_factory(
    PagamentoNotaFiscalItemForm,
    extra=0,
    can_delete=True,
)


class PagamentoNotaFiscalPagamentoForm(forms.ModelForm):
    valor = forms.CharField(
        label='Valor (R$)',
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control rounded-3 text-end',
                'data-mask': 'br-moeda',
                'inputmode': 'decimal',
                'autocomplete': 'off',
                'maxlength': '22',
                'placeholder': '0,00',
            }
        ),
    )
    acrescimos = forms.CharField(
        label='Acréscimos (R$)',
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control rounded-3 text-end',
                'data-mask': 'br-moeda',
                'inputmode': 'decimal',
                'autocomplete': 'off',
                'maxlength': '22',
                'placeholder': '0,00',
            }
        ),
    )
    descontos = forms.CharField(
        label='Descontos (R$)',
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control rounded-3 text-end',
                'data-mask': 'br-moeda',
                'inputmode': 'decimal',
                'autocomplete': 'off',
                'maxlength': '22',
                'placeholder': '0,00',
            }
        ),
    )

    class Meta:
        model = PagamentoNotaFiscalPagamento
        fields = ('tipo', 'data', 'valor', 'acrescimos', 'descontos', 'observacao')
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control rounded-3'}),
            'observacao': forms.TextInput(
                attrs={'class': 'form-control rounded-3', 'placeholder': 'Observação'}
            ),
        }

    def __init__(self, *args, **kwargs):
        default_data = kwargs.pop('default_data', None)
        super().__init__(*args, **kwargs)
        # Pagamento é opcional: pode salvar NF + itens e preencher depois.
        if 'tipo' in self.fields:
            self.fields['tipo'].required = False
        if 'data' in self.fields:
            self.fields['data'].required = False
        if 'observacao' in self.fields:
            self.fields['observacao'].required = False
        for field_name in ('valor', 'acrescimos', 'descontos'):
            self.fields[field_name].required = False
        if default_data and not self.is_bound and not self.initial.get('data'):
            self.initial['data'] = default_data.isoformat()
        if self.instance and self.instance.pk:
            self.initial['valor'] = format_decimal_br_moeda(self.instance.valor)
            self.initial['acrescimos'] = format_decimal_br_moeda(self.instance.acrescimos)
            self.initial['descontos'] = format_decimal_br_moeda(self.instance.descontos)
        else:
            self.initial.setdefault('valor', '0,00')
            self.initial.setdefault('acrescimos', '0,00')
            self.initial.setdefault('descontos', '0,00')

    def _raw_value(self, field_name: str) -> str:
        if not self.is_bound:
            return ''
        return str(self.data.get(self.add_prefix(field_name), '')).strip()

    def _linha_vazia(self) -> bool:
        zeros = ('', '0', '0,0', '0,00', '0.00')
        return (
            self._raw_value('tipo') == ''
            and self._raw_value('data') == ''
            and self._raw_value('valor') in zeros
            and self._raw_value('acrescimos') in zeros
            and self._raw_value('descontos') in zeros
            and self._raw_value('observacao') == ''
        )

    def clean_valor(self):
        raw = self.cleaned_data.get('valor')
        if self._linha_vazia() and raw in (None, '', '0', '0,0', '0,00'):
            return Decimal('0')
        if raw in (None, ''):
            return Decimal('0')
        return parse_valor_moeda_obrigatorio(raw)

    def clean_acrescimos(self):
        raw = self.cleaned_data.get('acrescimos')
        if raw in (None, '', '0', '0,0', '0,00'):
            return Decimal('0')
        return parse_valor_moeda_obrigatorio(raw)

    def clean_descontos(self):
        raw = self.cleaned_data.get('descontos')
        if raw in (None, '', '0', '0,0', '0,00'):
            return Decimal('0')
        return parse_valor_moeda_obrigatorio(raw)

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.valor = self.cleaned_data['valor']
        obj.acrescimos = self.cleaned_data['acrescimos']
        obj.descontos = self.cleaned_data['descontos']
        if commit:
            obj.full_clean()
            obj.save()
        return obj


PagamentoNotaFiscalPagamentoFormSet = formset_factory(
    PagamentoNotaFiscalPagamentoForm,
    extra=1,
    can_delete=True,
)

PagamentoNotaFiscalPagamentoEditFormSet = formset_factory(
    PagamentoNotaFiscalPagamentoForm,
    extra=0,
    can_delete=True,
)


class BoletoRascunhoForm(forms.Form):
    numero_doc = forms.CharField(
        label='Número doc',
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control rounded-3'}),
    )
    parcela = forms.IntegerField(
        label='Parcela',
        min_value=1,
        widget=forms.NumberInput(
            attrs={'class': 'form-control rounded-3', 'min': '1', 'readonly': 'readonly'}
        ),
    )
    vencimento = forms.DateField(
        label='Vencimento',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control rounded-3'}),
    )
    valor = forms.CharField(
        label='Valor (R$)',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control rounded-3 text-end',
                'data-mask': 'br-moeda',
                'inputmode': 'decimal',
                'autocomplete': 'off',
                'maxlength': '22',
                'placeholder': '0,00',
            }
        ),
    )

    def clean_valor(self):
        return parse_valor_moeda_obrigatorio(self.cleaned_data.get('valor'))


BoletoRascunhoFormSet = formset_factory(
    BoletoRascunhoForm,
    extra=0,
    can_delete=True,
)


class BoletoPagamentoForm(forms.Form):
    boleto = forms.ModelChoiceField(
        label='Boleto',
        queryset=BoletoPagamento.objects.none(),
        widget=forms.RadioSelect,
    )
    data_pagamento = forms.DateField(
        label='Data de pagamento',
        initial=timezone.localdate,
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={'type': 'date', 'class': 'form-control rounded-3'},
        ),
    )
    acrescimos = forms.CharField(
        label='Acréscimos (R$)',
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control rounded-3 text-end js-boleto-ajuste',
                'data-mask': 'br-moeda',
                'data-boleto-ajuste': 'acrescimos',
                'inputmode': 'decimal',
                'autocomplete': 'off',
                'maxlength': '22',
                'placeholder': '0,00',
            }
        ),
    )
    descontos = forms.CharField(
        label='Descontos (R$)',
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control rounded-3 text-end js-boleto-ajuste',
                'data-mask': 'br-moeda',
                'data-boleto-ajuste': 'descontos',
                'inputmode': 'decimal',
                'autocomplete': 'off',
                'maxlength': '22',
                'placeholder': '0,00',
            }
        ),
    )
    valor_pago = forms.CharField(
        label='Valor pago (R$)',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control rounded-3 text-end',
                'data-mask': 'br-moeda',
                'inputmode': 'decimal',
                'autocomplete': 'off',
                'maxlength': '22',
                'placeholder': '0,00',
            }
        ),
    )
    observacao = forms.CharField(
        label='Observações',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control rounded-3', 'rows': 3}),
    )

    def __init__(self, *args, boletos=None, selected_boleto=None, **kwargs):
        super().__init__(*args, **kwargs)
        boletos_qs = boletos or BoletoPagamento.objects.none()
        self.fields['boleto'].queryset = boletos_qs
        boleto_base = selected_boleto or boletos_qs.first()
        if boleto_base and not self.is_bound:
            self.initial.setdefault('boleto', boleto_base.pk)
            self.initial.setdefault('data_pagamento', boleto_base.data_pagamento or timezone.localdate())
            self.initial.setdefault(
                'valor_pago',
                format_decimal_br_moeda(boleto_base.valor_pago or boleto_base.valor),
            )
            self.initial.setdefault('acrescimos', format_decimal_br_moeda(boleto_base.acrescimos))
            self.initial.setdefault('descontos', format_decimal_br_moeda(boleto_base.descontos))
            self.initial.setdefault('observacao', boleto_base.observacao)

    def clean_acrescimos(self):
        raw = self.cleaned_data.get('acrescimos')
        if raw in (None, '', '0', '0,0', '0,00'):
            return Decimal('0')
        return parse_valor_moeda_obrigatorio(raw)

    def clean_descontos(self):
        raw = self.cleaned_data.get('descontos')
        if raw in (None, '', '0', '0,0', '0,00'):
            return Decimal('0')
        return parse_valor_moeda_obrigatorio(raw)

    def clean_valor_pago(self):
        return parse_valor_moeda_obrigatorio(self.cleaned_data.get('valor_pago'))

    def clean(self):
        cleaned_data = super().clean()
        valor_pago = cleaned_data.get('valor_pago')
        if valor_pago is not None and valor_pago <= 0:
            self.add_error('valor_pago', 'Informe um valor pago maior que zero.')
        return cleaned_data
