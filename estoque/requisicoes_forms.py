from __future__ import annotations

from django import forms
from django.db.models import Q
from django.forms import inlineformset_factory
from django.utils import timezone

from local.models import Local
from obras.models import Obra
from rh.models import Funcionario

from .models import Item, RequisicaoEstoque, RequisicaoEstoqueItem


class RequisicaoEstoqueForm(forms.ModelForm):
    # Inputs de busca (UI) + hidden com IDs (validação real)
    solicitante_nome = forms.CharField(required=False)
    local_nome = forms.CharField(required=False)

    class Meta:
        model = RequisicaoEstoque
        fields = ('solicitante', 'local', 'obra')
        widgets = {
            'solicitante': forms.HiddenInput(),
            'local': forms.HiddenInput(),
            'obra': forms.Select(attrs={'class': 'form-select rounded-3'}),
        }
        labels = {
            'solicitante': 'Solicitante',
            'local': 'Local',
            'obra': 'Obra',
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['solicitante'].queryset = Funcionario.objects.filter(
                empresa=empresa
            ).exclude(situacao_atual__in=['demitido', 'inativo']).order_by('nome')
            self.fields['local'].queryset = Local.objects.filter(empresa=empresa).order_by('nome')

            hoje = timezone.localdate()
            qs_ativas = Obra.objects.filter(empresa=empresa).filter(
                Q(data_fim__isnull=True) | Q(data_fim__gte=hoje)
            )
            # Se houver uma obra selecionada no POST, garanta que ela esteja no queryset,
            # mesmo se não passar pelo filtro de "ativa" (evita o campo zerar e invalidar o form).
            obra_sel = None
            try:
                raw = None
                if hasattr(self, 'data') and self.data is not None:
                    raw = (self.data.get('obra') or '').strip()
                if raw and raw.isdigit():
                    obra_sel = int(raw)
            except Exception:
                obra_sel = None
            if obra_sel:
                qs_ativas = (qs_ativas | Obra.objects.filter(empresa=empresa, pk=obra_sel)).distinct()
            self.fields['obra'].queryset = qs_ativas.order_by('nome')

        self.fields['local'].required = False
        self.fields['obra'].required = False


class RequisicaoEstoqueItemForm(forms.ModelForm):
    class Meta:
        model = RequisicaoEstoqueItem
        fields = ('item', 'quantidade')
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'quantidade': forms.NumberInput(
                attrs={'class': 'form-control rounded-3', 'step': '0.0001', 'min': 0}
            ),
        }
        labels = {
            'item': 'Item',
            'quantidade': 'Quantidade',
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['item'].queryset = Item.objects.filter(
                empresa=empresa, ativo=True
            ).select_related('unidade_medida').order_by('descricao')


RequisicaoEstoqueItemFormSet = inlineformset_factory(
    RequisicaoEstoque,
    RequisicaoEstoqueItem,
    form=RequisicaoEstoqueItemForm,
    extra=0,
    can_delete=True,
)


RequisicaoEstoqueItemFormSetEdit = inlineformset_factory(
    RequisicaoEstoque,
    RequisicaoEstoqueItem,
    form=RequisicaoEstoqueItemForm,
    extra=1,
    can_delete=True,
)

