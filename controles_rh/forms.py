from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from rh.models import Funcionario
from .models import (
    CestaBasicaItem,
    CestaBasicaLista,
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
            'valor_unitario',
            'viagens_dia',
            'dias',
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
            'valor_unitario': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'viagens_dia': forms.NumberInput(attrs={'step': '1', 'min': '0'}),
            'dias': forms.NumberInput(attrs={'step': '1', 'min': '0'}),
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
            'valor_unitario': 'Valor unitário',
            'viagens_dia': 'X',
            'dias': 'Dias',
            'valor_pagar': 'Valor Total de VT',
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
                    'valor_unitario': str(getattr(func, 'valor_vale_transporte', '') or ''),
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
        self.fields['valor_pagar'].help_text = 'Calculado automaticamente por valor unitário × dias.'
        self.fields['valor_pagar'].widget.attrs['readonly'] = 'readonly'

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


class CestaBasicaListaForm(BaseStyledModelForm):
    class Meta:
        model = CestaBasicaLista
        fields = [
            'titulo',
            'texto_declaracao',
            'data_emissao_recibo',
            'local_emissao',
            'recibo_altura_linha_pct',
            'observacao',
            'cb_calculo_automatico',
            'cb_status_manual',
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={'maxlength': 120}),
            'texto_declaracao': forms.Textarea(attrs={'rows': 3}),
            'data_emissao_recibo': forms.DateInput(attrs={'type': 'date'}),
            'local_emissao': forms.TextInput(attrs={'maxlength': 120}),
            'recibo_altura_linha_pct': forms.NumberInput(
                attrs={
                    'type': 'range',
                    'class': 'form-range',
                    'min': 70,
                    'max': 180,
                    'step': 5,
                }
            ),
            'observacao': forms.Textarea(attrs={'rows': 2}),
        }
        labels = {
            'titulo': 'Título interno',
            'texto_declaracao': 'Texto da declaração (rodapé)',
            'data_emissao_recibo': 'Data no rodapé do recibo',
            'local_emissao': 'Local (cidade/UF)',
            'recibo_altura_linha_pct': 'Altura da linha no PDF (tabela)',
            'observacao': 'Observação interna',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()
        self.fields['titulo'].required = False
        self.fields['texto_declaracao'].required = False
        self.fields['data_emissao_recibo'].required = False
        self.fields['observacao'].required = False
        df = self.fields['data_emissao_recibo']
        df.widget.format = '%Y-%m-%d'
        df.input_formats = ['%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y']
        self.fields['texto_declaracao'].help_text = (
            'Vazio = declaração padrão com o nome da empresa (definida no sistema).'
        )
        self.fields['local_emissao'].help_text = (
            'Cidade/UF no rodapé do recibo. Vazio = PARNAMIRIM - RN (padrão do sistema).'
        )
        self.fields['recibo_altura_linha_pct'].help_text = (
            'Afeta recibo e relatório em PDF: 100% = padrão; aumente para linhas mais altas.'
        )
        self.fields['cb_status_manual'].required = False


class CestaBasicaItemForm(BaseStyledModelForm):
    class Meta:
        model = CestaBasicaItem
        fields = ['funcionario', 'nome', 'funcao', 'lotacao', 'recebido', 'data_recebimento', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'maxlength': 150}),
            'funcao': forms.TextInput(attrs={'maxlength': 120}),
            'lotacao': forms.TextInput(attrs={'maxlength': 120}),
            'data_recebimento': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'funcionario': 'Funcionário',
            'nome': 'Empregado',
            'funcao': 'Função',
            'lotacao': 'Lotação',
            'recebido': 'Já recebeu a cesta',
            'data_recebimento': 'Data de recebimento',
            'ativo': 'Ativo',
        }

    def __init__(self, *args, **kwargs):
        self.lista = kwargs.pop('lista', None)
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()
        self.fields['funcionario'].required = False
        self.fields['nome'].required = False
        self.fields['funcao'].required = False
        self.fields['lotacao'].required = False

        if self.lista:
            empresa = self.lista.competencia.empresa
            q_func = Q(empresa=empresa, situacao_atual='admitido')
            if self.instance and self.instance.pk and self.instance.funcionario_id:
                q_func |= Q(pk=self.instance.funcionario_id)
            funcionarios_qs = (
                Funcionario.objects.filter(q_func)
                .select_related('cargo', 'banco', 'lotacao')
                .distinct()
                .order_by('nome')
            )
            self.fields['funcionario'].queryset = funcionarios_qs

            self.funcionarios_data = {
                str(func.pk): {
                    'nome': getattr(func, 'nome', '') or '',
                    'funcao': str(getattr(func, 'cargo', '') or ''),
                    'lotacao': (
                        func.lotacao.nome
                        if getattr(func, 'lotacao_id', None)
                        else ''
                    ),
                }
                for func in funcionarios_qs
            }
        else:
            self.funcionarios_data = {}

        self.fields['nome'].help_text = 'Pode ser preenchido ao escolher o funcionário ou digitado manualmente.'
        self.fields['funcao'].help_text = 'Pode vir do cargo do funcionário ou ser editada.'
        self.fields['lotacao'].help_text = (
            'Preenchida automaticamente com a lotação do cadastro do funcionário; pode ser alterada.'
        )
        self.fields['data_recebimento'].required = False
        self.fields['data_recebimento'].help_text = (
            'Ao marcar “Recebeu” na lista, a data de hoje é sugerida automaticamente se estiver vazia.'
        )
        df = self.fields['data_recebimento']
        df.widget.format = '%Y-%m-%d'
        df.input_formats = ['%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y']

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.lista and not instance.pk:
            instance.lista = self.lista
        if commit:
            instance.save()
        return instance