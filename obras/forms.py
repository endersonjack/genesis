from decimal import Decimal, InvalidOperation

from django import forms

from .models import Obra


def _format_decimal_br_moeda(d: Decimal) -> str:
    """Exibe Decimal no padrão 1.234,56 (máscara br-moeda)."""
    d = d.quantize(Decimal('0.01'))
    neg = d < 0
    d = abs(d)
    whole = int(d)
    frac = int((d - Decimal(whole)) * 100)
    if whole == 0:
        intp = '0'
    else:
        s = str(whole)
        blocks = []
        while s:
            blocks.append(s[-3:])
            s = s[:-3]
        intp = '.'.join(reversed(blocks))
    out = f'{intp},{frac:02d}'
    return ('-' if neg else '') + out


def _parse_valor_moeda(raw) -> Decimal | None:
    """
    Aceita valor já normalizado pelo JS (1234.56), formato BR (1.234,56)
    ou só vírgula como decimal (1234,56).
    """
    if raw is None:
        return None
    s = (
        str(raw)
        .strip()
        .replace(' ', '')
        .replace('R$', '')
        .replace('r$', '')
    )
    if not s:
        return None
    if s in ('-', ',', '.'):
        raise forms.ValidationError('Informe um valor numérico válido.')
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    else:
        if s.count('.') > 1:
            s = s.replace('.', '')
    try:
        d = Decimal(s)
    except InvalidOperation:
        raise forms.ValidationError('Informe um valor numérico válido.')
    if d < 0:
        raise forms.ValidationError('O valor não pode ser negativo.')
    if d == 0:
        return None
    if abs(d) >= Decimal('1e15'):
        raise forms.ValidationError('Valor inválido.')
    return d.quantize(Decimal('0.01'))


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
            'data_inicio': forms.DateInput(
                attrs={'class': 'form-control rounded-3', 'type': 'date'}
            ),
            'prazo': forms.TextInput(attrs={'class': 'form-control rounded-3'}),
            'data_fim': forms.DateInput(
                attrs={'class': 'form-control rounded-3', 'type': 'date'}
            ),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
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

        if self.instance.pk and self.instance.valor is not None:
            self.initial['valor'] = _format_decimal_br_moeda(self.instance.valor)

    def clean_valor(self):
        return _parse_valor_moeda(self.cleaned_data.get('valor'))
