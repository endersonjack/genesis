from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.utils import timezone

from .models import ListaCompraEstoque, ListaCompraEstoqueItem


class ListaCompraEstoqueForm(forms.ModelForm):
    class Meta:
        model = ListaCompraEstoque
        fields = ('nome', 'data_pedido', 'status', 'observacoes')
        widgets = {
            'nome': forms.TextInput(
                attrs={
                    'class': 'form-control rounded-3',
                    'placeholder': 'Ex.: Compras semana 15 — Obra Centro',
                    'maxlength': 200,
                }
            ),
            # type="date" só aceita valor ISO (YYYY-MM-DD); sem format o Django usa
            # formato local (ex.: dd/mm/aaaa) e o campo aparece vazio no navegador.
            'data_pedido': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-control rounded-3', 'type': 'date'},
            ),
            'status': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'observacoes': forms.Textarea(
                attrs={
                    'class': 'form-control rounded-3',
                    'rows': 3,
                    'placeholder': 'Observações gerais sobre o pedido (opcional)',
                }
            ),
        }
        labels = {
            'nome': 'Nome da lista',
            'data_pedido': 'Data do pedido',
            'status': 'Status',
            'observacoes': 'Observações gerais',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dp = self.fields['data_pedido']
        dp.widget.format = '%Y-%m-%d'
        dp.input_formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d/%m/%y',
            '%d.%m.%Y',
        ]
        if (
            not self.is_bound
            and not getattr(self.instance, 'pk', None)
            and self.initial.get('data_pedido') is None
        ):
            self.initial['data_pedido'] = timezone.localdate()


class ListaCompraEstoqueItemForm(forms.ModelForm):
    class Meta:
        model = ListaCompraEstoqueItem
        fields = ('item', 'quantidade_comprar', 'observacoes')
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'quantidade_comprar': forms.NumberInput(
                attrs={
                    'class': 'form-control rounded-3',
                    'step': '0.0001',
                    'min': 0,
                }
            ),
            'observacoes': forms.TextInput(
                attrs={
                    'class': 'form-control rounded-3',
                    'placeholder': 'Obs. do item (opcional)',
                }
            ),
        }
        labels = {
            'item': 'Item',
            'quantidade_comprar': 'Qtd. a comprar',
            'observacoes': 'Obs. do item',
        }


class ListaCompraEstoqueItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        valid = 0
        seen_items: set[int] = set()
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            if not hasattr(form, 'cleaned_data'):
                continue
            cd = form.cleaned_data
            item = cd.get('item')
            q = cd.get('quantidade_comprar')
            if item is None or q is None:
                continue
            pk = item.pk
            if pk in seen_items:
                raise ValidationError(
                    'Não inclua o mesmo item em mais de uma linha.'
                )
            seen_items.add(pk)
            if q > 0:
                valid += 1
        if valid < 1:
            raise ValidationError(
                'Inclua ao menos um item com quantidade a comprar maior que zero.'
            )


def _factory_lista_compra_item_formset(extra: int):
    return inlineformset_factory(
        ListaCompraEstoque,
        ListaCompraEstoqueItem,
        form=ListaCompraEstoqueItemForm,
        formset=ListaCompraEstoqueItemFormSet,
        extra=extra,
        can_delete=True,
    )


ListaCompraEstoqueItemFormSetNova = _factory_lista_compra_item_formset(0)
ListaCompraEstoqueItemFormSetEdit = _factory_lista_compra_item_formset(0)
