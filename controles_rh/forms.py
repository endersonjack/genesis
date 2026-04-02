from django import forms
from django.core.exceptions import ValidationError

from rh.models import Funcionario
from .models import (
    Competencia,
    STATUS_PAGAMENTO_VT_CHOICES,
    ValeTransporteItem,
    ValeTransporteTabela,
)


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

    def clean(self):
        cleaned_data = super().clean()
        mes = cleaned_data.get('mes')
        ano = cleaned_data.get('ano')

        if self.empresa_ativa and mes is not None and ano is not None:
            qs = Competencia.objects.filter(
                empresa=self.empresa_ativa,
                mes=mes,
                ano=ano,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    'Já existe competência para este mês e ano nesta empresa.',
                    code='duplicate_competencia',
                )

        return cleaned_data

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
            'vt_calculo_automatico',
            'vt_status_manual',
        ]
        widgets = {
            'descricao': forms.Textarea(attrs={
                'rows': 3,
            }),
        }
        labels = {
            'nome': 'Nome da tabela',
            'descricao': 'Descrição',
            'vt_calculo_automatico': 'Calcular status automaticamente pelos itens',
            'vt_status_manual': 'Status de pagamento (manual)',
        }

    def __init__(self, *args, **kwargs):
        self.competencia = kwargs.pop('competencia', None)
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()

        self.fields['descricao'].required = False

        self.fields['nome'].help_text = 'Ex.: VT Escritório, VT Obra A, VT Equipe Externa.'
        self.fields['descricao'].help_text = 'Opcional.'
        self.fields['vt_calculo_automatico'].help_text = (
            'Automático: calcula pelos itens (saldo a pagar × pago). '
            'Manual: você escolhe o status abaixo, ignorando os valores das linhas.'
        )
        self.fields['vt_status_manual'].required = False
        self.fields['vt_status_manual'].help_text = (
            'Obrigatório se desmarcar o cálculo automático.'
        )
        self.fields['vt_status_manual'].choices = [
            ('', '— Selecione —'),
        ] + list(STATUS_PAGAMENTO_VT_CHOICES)

    def clean(self):
        cleaned_data = super().clean()
        auto = cleaned_data.get('vt_calculo_automatico')
        manual = cleaned_data.get('vt_status_manual')
        if auto is False and not manual:
            self.add_error(
                'vt_status_manual',
                'Selecione o status de pagamento ou marque o modo automático.',
            )
        if auto is True:
            cleaned_data['vt_status_manual'] = None
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.competencia and not instance.pk:
            instance.competencia = self.competencia

        if commit:
            instance.save()

        return instance


class ValeTransporteItemPagamentoForm(BaseStyledModelForm):
    """Modal rápido: apenas valor pago e data de pagamento."""

    class Meta:
        model = ValeTransporteItem
        fields = ['valor_pago', 'data_pagamento']
        widgets = {
            'valor_pago': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            # type="date" exige value em ISO (YYYY-MM-DD); locale pt-BR quebrava o valor inicial
            'data_pagamento': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d',
            ),
        }
        labels = {
            'valor_pago': 'Valor pago',
            'data_pagamento': 'Data de pagamento',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()
        self.fields['valor_pago'].required = False
        self.fields['data_pagamento'].required = False
        self.fields['data_pagamento'].help_text = 'Opcional.'
        dp = self.fields['data_pagamento']
        dp.widget.format = '%Y-%m-%d'
        dp.input_formats = ['%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y']


class ValeTransporteItemForm(BaseStyledModelForm):
    class Meta:
        model = ValeTransporteItem
        fields = [
            'funcionario',
            'nome',
            'funcao',
            'endereco',
            'valor_pagar',
            'valor_pago',
            'data_pagamento',
            'pix',
            'tipo_pix',
            'banco',
            'observacao',
            'ativo',
        ]
        widgets = {
            'observacao': forms.Textarea(attrs={'rows': 2}),
            'valor_pagar': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'valor_pago': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            # type="date" exige value ISO (YYYY-MM-DD)
            'data_pagamento': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d',
            ),
        }
        labels = {
            'funcionario': 'Funcionário',
            'nome': 'Nome',
            'funcao': 'Função',
            'endereco': 'Endereço',
            'valor_pagar': 'Valor a pagar',
            'valor_pago': 'Valor pago',
            'data_pagamento': 'Data de pagamento',
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

        if 'data_pagamento' in self.fields:
            dp = self.fields['data_pagamento']
            dp.widget.format = '%Y-%m-%d'
            dp.input_formats = ['%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y']
            dp.help_text = 'Opcional. Data do último pagamento registrado.'

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
        self.fields['valor_pago'].help_text = 'Informe o quanto já foi pago nesta linha; a linha fica verde quando o valor pago cobre o valor a pagar.'

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