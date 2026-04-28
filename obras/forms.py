from decimal import Decimal

from django import forms

from core.moeda_fmt import format_decimal_br_moeda, parse_valor_moeda_br

from .models import Obra


class ObraForm(forms.ModelForm):
    # CharField: DecimalField do Django rejeita 1.234,56 se o JS não normalizar a tempo.
    valor = forms.CharField(
        label='Valor (R$)',
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control rounded-3 text-end',
                'data-mask': 'br-moeda',
                'inputmode': 'decimal',
                'autocomplete': 'off',
                'maxlength': '20',
                'placeholder': '0,00',
            }
        ),
    )

    class Meta:
        model = Obra
        fields = (
            'nome',
            'contratante',
            'objeto',
            'endereco',
            'cno',
            'valor',
            'secretaria',
            'gestor',
            'fiscal',
            'data_inicio',
            'prazo',
            'data_fim',
        )
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'contratante': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'objeto': forms.Textarea(
                attrs={'class': 'form-control rounded-3', 'rows': 3}
            ),
            'endereco': forms.Textarea(
                attrs={'class': 'form-control rounded-3', 'rows': 2}
            ),
            'cno': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'secretaria': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'gestor': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'fiscal': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            # HTML5 date precisa de value em ISO (YYYY-MM-DD) para exibir corretamente.
            'data_inicio': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-control rounded-3', 'type': 'date'},
            ),
            'prazo': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'data_fim': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-control rounded-3', 'type': 'date'},
            ),
        }

    def __init__(self, *args, empresa=None, can_edit_valor=False, **kwargs):
        self.empresa = empresa
        self.can_edit_valor = bool(can_edit_valor)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['contratante'].queryset = (
                empresa.clientes.all().order_by('nome')
            )
        self.fields['objeto'].required = False
        self.fields['endereco'].required = False
        self.fields['cno'].required = False
        self.fields['secretaria'].required = False
        self.fields['gestor'].required = False
        self.fields['fiscal'].required = False
        self.fields['data_inicio'].required = False
        self.fields['prazo'].required = False
        self.fields['data_fim'].required = False

        if not self.can_edit_valor:
            # Segurança: não renderiza nem aceita edição do valor para não-admins.
            self.fields.pop('valor', None)
            self.initial.pop('valor', None)
        elif self.instance.pk and self.instance.valor is not None:
            self.initial['valor'] = format_decimal_br_moeda(self.instance.valor)

    def clean_valor(self):
        return parse_valor_moeda_br(self.cleaned_data.get('valor'))
