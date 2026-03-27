from django import forms

from rh.models import Funcionario
from .models import Competencia, ValeTransporteItem, ValeTransporteTabela


class BaseStyledModelForm(forms.ModelForm):
    """
    Form base para aplicar classes padrão do Bootstrap.
    """

    def apply_bootstrap_classes(self):
        for field_name, field in self.fields.items():
            widget = field.widget

            if isinstance(widget, forms.CheckboxInput):
                existing_class = widget.attrs.get('class', '')
                widget.attrs['class'] = f'{existing_class} form-check-input'.strip()
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                existing_class = widget.attrs.get('class', '')
                widget.attrs['class'] = f'{existing_class} form-select'.strip()
            elif isinstance(widget, forms.FileInput):
                existing_class = widget.attrs.get('class', '')
                widget.attrs['class'] = f'{existing_class} form-control'.strip()
            elif isinstance(widget, forms.Textarea):
                existing_class = widget.attrs.get('class', '')
                widget.attrs['class'] = f'{existing_class} form-control'.strip()
            else:
                existing_class = widget.attrs.get('class', '')
                widget.attrs['class'] = f'{existing_class} form-control'.strip()

            if field.required and not isinstance(widget, forms.CheckboxInput):
                placeholder = widget.attrs.get('placeholder')
                if not placeholder:
                    widget.attrs['placeholder'] = field.label or field_name.replace('_', ' ').title()


class CompetenciaForm(BaseStyledModelForm):
    class Meta:
        model = Competencia
        fields = [
            'mes',
            'ano',
            'titulo',
            'fechada',
            'observacao',
        ]
        widgets = {
            'mes': forms.NumberInput(attrs={
                'min': 1,
                'max': 12,
            }),
            'ano': forms.NumberInput(attrs={
                'min': 2000,
                'max': 2100,
            }),
            'titulo': forms.TextInput(attrs={
                'maxlength': 30,
            }),
            'observacao': forms.Textarea(attrs={
                'rows': 3,
            }),
        }
        labels = {
            'mes': 'Mês',
            'ano': 'Ano',
            'titulo': 'Título',
            'fechada': 'Fechada',
            'observacao': 'Observação',
        }

    def __init__(self, *args, **kwargs):
        self.empresa_ativa = kwargs.pop('empresa_ativa', None)
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()

        self.fields['mes'].help_text = 'Informe o mês da competência.'
        self.fields['ano'].help_text = 'Informe o ano da competência.'
        self.fields['titulo'].help_text = 'Opcional. Se vazio, será gerado automaticamente.'
        self.fields['observacao'].required = False

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.empresa_ativa and not instance.pk:
            instance.empresa = self.empresa_ativa

        if commit:
            instance.save()

        return instance


class ValeTransporteTabelaForm(BaseStyledModelForm):
    class Meta:
        model = ValeTransporteTabela
        fields = [
            'nome',
            'descricao',
            'ordem',
            'ativa',
            'fechada',
        ]
        widgets = {
            'descricao': forms.Textarea(attrs={
                'rows': 3,
            }),
            'ordem': forms.NumberInput(attrs={
                'min': 0,
            }),
        }
        labels = {
            'nome': 'Nome da tabela',
            'descricao': 'Descrição',
            'ordem': 'Ordem',
            'ativa': 'Ativa',
            'fechada': 'Fechada',
        }

    def __init__(self, *args, **kwargs):
        self.competencia = kwargs.pop('competencia', None)
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()

        self.fields['descricao'].required = False
        self.fields['ordem'].required = False

        self.fields['nome'].help_text = 'Ex.: VT Escritório, VT Obra A, VT Equipe Externa.'
        self.fields['descricao'].help_text = 'Opcional.'
        self.fields['ordem'].help_text = 'Use para definir a ordem de exibição.'

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.competencia and not instance.pk:
            instance.competencia = self.competencia

        if commit:
            instance.save()

        return instance


class ValeTransporteItemForm(BaseStyledModelForm):
    class Meta:
        model = ValeTransporteItem
        fields = [
            'funcionario',
            'nome',
            'funcao',
            'endereco',
            'valor_pagar',
            'pix',
            'tipo_pix',
            'banco',
            'observacao',
            'ativo',
        ]
        widgets = {
            'observacao': forms.Textarea(attrs={'rows': 3}),
            'valor_pagar': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
        labels = {
            'funcionario': 'Funcionário',
            'nome': 'Nome',
            'funcao': 'Função',
            'endereco': 'Endereço',
            'valor_pagar': 'Valor a pagar',
            'pix': 'Chave Pix',
            'tipo_pix': 'Tipo Pix',
            'banco': 'Banco',
            'observacao': 'Observação',
            'ativo': 'Ativo',
        }

    def __init__(self, *args, **kwargs):
        self.tabela = kwargs.pop('tabela', None)
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()

        self.fields['funcionario'].required = False
        self.fields['observacao'].required = False

        if self.tabela:
            empresa = self.tabela.competencia.empresa
            funcionarios_qs = Funcionario.objects.filter(
                empresa=empresa,
                situacao_atual='admitido',
            ).select_related('cargo', 'banco').order_by('nome')

            self.fields['funcionario'].queryset = funcionarios_qs

            # mapa para auto preencher no modal
            self.funcionarios_data = {
                str(func.pk): {
                    'nome': getattr(func, 'nome', '') or '',
                    'funcao': str(getattr(func, 'cargo', '') or ''),
                    'endereco': getattr(func, 'endereco_completo', '') or '',
                    'valor_vale_transporte': str(getattr(func, 'valor_vale_transporte', '') or ''),
                    'pix': getattr(func, 'pix', '') or '',
                    'tipo_pix': getattr(func, 'tipo_pix', '') or '',
                    'banco': str(getattr(func, 'banco', '') or ''),
                }
                for func in funcionarios_qs
            }
        else:
            self.funcionarios_data = {}

        self.fields['nome'].help_text = 'Pode ser preenchido automaticamente pelo funcionário ou alterado manualmente.'
        self.fields['funcao'].help_text = 'Pode ser alterada manualmente.'
        self.fields['endereco'].help_text = 'Pode ser alterado manualmente.'

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.tabela and not instance.pk:
            instance.tabela = self.tabela

        if instance.funcionario:
            cargo = getattr(instance.funcionario, 'cargo', None)
            banco = getattr(instance.funcionario, 'banco', None)

            if not instance.nome:
                instance.nome = getattr(instance.funcionario, 'nome', '') or ''
            if not instance.funcao:
                instance.funcao = str(cargo) if cargo else ''
            if not instance.endereco:
                instance.endereco = getattr(instance.funcionario, 'endereco_completo', '') or ''
            if not instance.pix:
                instance.pix = getattr(instance.funcionario, 'pix', '') or ''
            if not instance.tipo_pix:
                instance.tipo_pix = getattr(instance.funcionario, 'tipo_pix', '') or ''
            if not instance.banco:
                instance.banco = str(banco) if banco else ''

        if commit:
            instance.save()

        return instance