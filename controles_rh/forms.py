from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from rh.models import Funcionario
from .models import (
    AlteracaoFolhaLinha,
    AnexoDiversoCompetencia,
    CestaBasicaItem,
    CestaBasicaLista,
    Competencia,
    PagamentoSalarioControle,
    PagamentoSalarioLinha,
    PremiacaoFuncionario,
    STATUS_PAGAMENTO_VT_CHOICES,
    ValeTransporteItem,
    ValeTransporteTabela,
)


ALLOWED_ANEXO_DIVERSO_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp',
    'pdf',
    'doc', 'docx',
    'xls', 'xlsx', 'xlsm', 'xlsb',
}


def _decimal_input_ptbr(value) -> str:
    try:
        d = Decimal(str(value if value is not None else 0))
    except (InvalidOperation, TypeError, ValueError):
        d = Decimal('0')
    return f'{d.quantize(Decimal("0.01")):.2f}'.replace('.', ',')



def _horas_minutos_partes(value) -> tuple[int, int]:
    try:
        horas_decimais = Decimal(str(value if value is not None else 0))
    except (InvalidOperation, TypeError, ValueError):
        horas_decimais = Decimal('0')
    if horas_decimais < 0:
        horas_decimais = Decimal('0')
    total_minutos = int((horas_decimais * Decimal('60')).quantize(Decimal('1')))
    return divmod(total_minutos, 60)


def _decimal_de_horas_minutos(horas, minutos) -> Decimal:
    try:
        h = int(horas or 0)
        m = int(minutos or 0)
    except (TypeError, ValueError):
        raise ValidationError('Informe horas e minutos válidos.')
    if h < 0 or m < 0 or m > 59:
        raise ValidationError('Informe minutos entre 0 e 59.')
    return (Decimal(h) + (Decimal(m) / Decimal('60'))).quantize(Decimal('0.01'))


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
        self._original_funcao = getattr(self.instance, 'funcao', '') or ''
        self.apply_bootstrap_classes()

        self.fields['funcionario'].required = False
        self.fields['observacao'].required = False

        if 'data_pagamento' in self.fields:
            dp = self.fields['data_pagamento']
            dp.widget.format = '%Y-%m-%d'
            dp.input_formats = ['%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y']

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
                    'cpf': getattr(func, 'cpf', '') or '',
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

        self.fields['funcao'].disabled = True
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
            instance.funcao = str(cargo) if cargo else ''
            if not instance.endereco:
                instance.endereco = getattr(instance.funcionario, 'endereco_completo', '') or ''
            if not instance.pix:
                instance.pix = getattr(instance.funcionario, 'pix', '') or ''
            if not instance.tipo_pix:
                instance.tipo_pix = getattr(instance.funcionario, 'tipo_pix', '') or ''
            if not instance.banco:
                instance.banco = str(banco) if banco else ''
        else:
            instance.funcao = self._original_funcao

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
    tipo_cesta_basica = forms.ChoiceField(
        choices=Funcionario.TIPO_CESTA_BASICA_CHOICES,
        label='Tipo Cesta Básica',
        required=False,
    )

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
            'lotacao': 'Local de Trabalho',
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
        self.fields['tipo_cesta_basica'].required = False

        if self.instance and self.instance.pk and self.instance.funcionario_id:
            self.fields['tipo_cesta_basica'].initial = (
                self.instance.funcionario.tipo_cesta_basica
                or Funcionario.TIPO_CESTA_BASICA_RECEBE
            )
        else:
            self.fields['tipo_cesta_basica'].initial = Funcionario.TIPO_CESTA_BASICA_RECEBE

        if self.lista:
            empresa = self.lista.competencia.empresa
            q_func = Q(empresa=empresa, situacao_atual='admitido')
            if self.instance and self.instance.pk and self.instance.funcionario_id:
                q_func |= Q(pk=self.instance.funcionario_id)
            funcionarios_qs = (
                Funcionario.objects.filter(q_func)
                .select_related('cargo', 'banco', 'local_trabalho')
                .distinct()
                .order_by('nome')
            )
            self.fields['funcionario'].queryset = funcionarios_qs

            self.funcionarios_data = {
                str(func.pk): {
                    'nome': getattr(func, 'nome', '') or '',
                    'funcao': str(getattr(func, 'cargo', '') or ''),
                    'lotacao': (
                        func.local_trabalho.nome
                        if getattr(func, 'local_trabalho_id', None)
                        else ''
                    ),
                    'tipo_cesta_basica': (
                        getattr(func, 'tipo_cesta_basica', '')
                        or Funcionario.TIPO_CESTA_BASICA_RECEBE
                    ),
                }
                for func in funcionarios_qs
            }
        else:
            self.funcionarios_data = {}

        self.fields['nome'].help_text = 'Pode ser preenchido ao escolher o funcionário ou digitado manualmente.'
        self.fields['funcao'].help_text = 'Pode vir do cargo do funcionário ou ser editada.'
        self.fields['lotacao'].help_text = (
            'Preenchido automaticamente com o local de trabalho do cadastro do funcionário; pode ser alterado.'
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
        tipo_cesta_basica = self.cleaned_data.get('tipo_cesta_basica')
        if instance.funcionario_id and tipo_cesta_basica:
            funcionario = instance.funcionario
            if funcionario.tipo_cesta_basica != tipo_cesta_basica:
                funcionario.tipo_cesta_basica = tipo_cesta_basica
                funcionario.save(update_fields=['tipo_cesta_basica', 'atualizado_em'])
        if commit:
            instance.save()
        return instance


class AnexoDiversoCompetenciaForm(BaseStyledModelForm):
    class Meta:
        model = AnexoDiversoCompetencia
        fields = ['nome', 'descricao', 'arquivo']
        widgets = {
            'nome': forms.TextInput(attrs={'maxlength': 150}),
            'descricao': forms.Textarea(attrs={'rows': 2}),
            'arquivo': forms.FileInput(attrs={
                'accept': (
                    'image/*,.pdf,.doc,.docx,'
                    '.xls,.xlsx,.xlsm,.xlsb'
                ),
            }),
        }
        labels = {
            'nome': 'Nome',
            'descricao': 'Descrição',
            'arquivo': 'Anexar',
        }

    def __init__(self, *args, **kwargs):
        self.competencia = kwargs.pop('competencia', None)
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()
        self.fields['descricao'].required = False
        self.fields['arquivo'].help_text = 'Imagem, PDF, Word ou Excel.'

    def clean_arquivo(self):
        arquivo = self.cleaned_data.get('arquivo')
        if not arquivo:
            return arquivo
        nome = getattr(arquivo, 'name', '') or ''
        ext = nome.rsplit('.', 1)[-1].lower() if '.' in nome else ''
        if ext not in ALLOWED_ANEXO_DIVERSO_EXTENSIONS:
            raise ValidationError('Envie imagem, PDF, Word ou Excel.')
        return arquivo

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.competencia and not instance.pk:
            instance.competencia = self.competencia
        if self.usuario and not instance.pk:
            instance.usuario = self.usuario
        if commit:
            instance.save()
        return instance


class AlteracaoFolhaLinhaForm(BaseStyledModelForm):
    class Meta:
        model = AlteracaoFolhaLinha
        fields = [
            'hora_extra',
            'horas_feriado',
            'adicional',
            'outro_adicional',
            'descontos',
            'outro_desconto',
        ]
        widgets = {
            'hora_extra': forms.TextInput(
                attrs={
                    'data-mask': 'br-hours',
                    'inputmode': 'numeric',
                    'autocomplete': 'off',
                    'maxlength': '12',
                    'placeholder': '0h00m',
                    'class': 'text-end',
                }
            ),
            'horas_feriado': forms.TextInput(
                attrs={
                    'data-mask': 'br-hours',
                    'inputmode': 'numeric',
                    'autocomplete': 'off',
                    'maxlength': '12',
                    'placeholder': '0h00m',
                    'class': 'text-end',
                }
            ),
            'adicional': forms.TextInput(
                attrs={
                    'data-mask': 'br-moeda',
                    'inputmode': 'decimal',
                    'autocomplete': 'off',
                    'maxlength': '20',
                    'placeholder': '0,00',
                    'class': 'text-end',
                }
            ),
            'outro_adicional': forms.TextInput(
                attrs={
                    'data-mask': 'br-moeda',
                    'inputmode': 'decimal',
                    'autocomplete': 'off',
                    'maxlength': '20',
                    'placeholder': '0,00',
                    'class': 'text-end',
                }
            ),
            'descontos': forms.TextInput(
                attrs={
                    'data-mask': 'br-moeda',
                    'inputmode': 'decimal',
                    'autocomplete': 'off',
                    'maxlength': '20',
                    'placeholder': '0,00',
                    'class': 'text-end',
                }
            ),
            'outro_desconto': forms.TextInput(
                attrs={
                    'data-mask': 'br-moeda',
                    'inputmode': 'decimal',
                    'autocomplete': 'off',
                    'maxlength': '20',
                    'placeholder': '0,00',
                    'class': 'text-end',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hora_extra_horas'] = forms.IntegerField(
            label='Horas',
            required=False,
            min_value=0,
            widget=forms.NumberInput(attrs={
                'min': '0',
                'step': '1',
                'inputmode': 'numeric',
                'placeholder': '0',
                'data-af-time-input': '1',
                'class': 'text-end',
            }),
        )
        self.fields['hora_extra_minutos'] = forms.IntegerField(
            label='Minutos',
            required=False,
            min_value=0,
            max_value=59,
            widget=forms.NumberInput(attrs={
                'min': '0',
                'max': '59',
                'step': '1',
                'inputmode': 'numeric',
                'placeholder': '0',
                'data-af-time-input': '1',
                'class': 'text-end',
            }),
        )
        self.fields['horas_feriado_horas'] = forms.IntegerField(
            label='Horas',
            required=False,
            min_value=0,
            widget=forms.NumberInput(attrs={
                'min': '0',
                'step': '1',
                'inputmode': 'numeric',
                'placeholder': '0',
                'data-af-time-input': '1',
                'class': 'text-end',
            }),
        )
        self.fields['horas_feriado_minutos'] = forms.IntegerField(
            label='Minutos',
            required=False,
            min_value=0,
            max_value=59,
            widget=forms.NumberInput(attrs={
                'min': '0',
                'max': '59',
                'step': '1',
                'inputmode': 'numeric',
                'placeholder': '0',
                'data-af-time-input': '1',
                'class': 'text-end',
            }),
        )
        self.apply_bootstrap_classes()
        for name in self.fields:
            self.fields[name].required = False
        self.fields['adicional'].label = 'Adicional (%)'
        if not self.is_bound and self.instance:
            he_h, he_m = _horas_minutos_partes(getattr(self.instance, 'hora_extra', 0))
            hf_h, hf_m = _horas_minutos_partes(getattr(self.instance, 'horas_feriado', 0))
            self.initial['hora_extra_horas'] = he_h
            self.initial['hora_extra_minutos'] = he_m
            self.initial['horas_feriado_horas'] = hf_h
            self.initial['horas_feriado_minutos'] = hf_m
            for name in self.Meta.fields:
                if name not in ('hora_extra', 'horas_feriado'):
                    self.initial[name] = _decimal_input_ptbr(getattr(self.instance, name, 0))

    def clean(self):
        cleaned = super().clean()
        z = Decimal('0')
        try:
            cleaned['hora_extra'] = _decimal_de_horas_minutos(
                cleaned.get('hora_extra_horas'),
                cleaned.get('hora_extra_minutos'),
            )
        except ValidationError as exc:
            self.add_error('hora_extra_minutos', exc)
        try:
            cleaned['horas_feriado'] = _decimal_de_horas_minutos(
                cleaned.get('horas_feriado_horas'),
                cleaned.get('horas_feriado_minutos'),
            )
        except ValidationError as exc:
            self.add_error('horas_feriado_minutos', exc)
        for name in self.Meta.fields:
            if name not in cleaned:
                continue
            if cleaned[name] is None:
                cleaned[name] = z
        return cleaned


class PremiacaoFuncionarioForm(BaseStyledModelForm):
    class Meta:
        model = PremiacaoFuncionario
        fields = [
            'premio_atual',
            'premio_anterior',
            'media_premiacao',
        ]
        widgets = {
            'premio_atual': forms.TextInput(
                attrs={
                    'data-mask': 'br-moeda',
                    'inputmode': 'decimal',
                    'autocomplete': 'off',
                    'maxlength': '20',
                    'placeholder': '0,00',
                    'class': 'text-end',
                }
            ),
            'premio_anterior': forms.TextInput(
                attrs={
                    'data-mask': 'br-moeda',
                    'inputmode': 'decimal',
                    'autocomplete': 'off',
                    'maxlength': '20',
                    'placeholder': '0,00',
                    'class': 'text-end',
                }
            ),
            'media_premiacao': forms.TextInput(
                attrs={
                    'data-mask': 'br-moeda',
                    'inputmode': 'decimal',
                    'autocomplete': 'off',
                    'maxlength': '20',
                    'placeholder': '0,00',
                    'class': 'text-end',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()
        for name in self.fields:
            self.fields[name].required = False
        for name in ('premio_anterior', 'media_premiacao'):
            self.fields[name].disabled = True
            self.fields[name].widget.attrs.update({
                'disabled': 'disabled',
                'title': 'Valor calculado automaticamente.',
            })
        if not self.is_bound and self.instance:
            for name in self.Meta.fields:
                self.initial[name] = _decimal_input_ptbr(getattr(self.instance, name, 0))

    def clean(self):
        cleaned = super().clean()
        z = Decimal('0')
        for name in self.Meta.fields:
            if name not in cleaned:
                continue
            if cleaned[name] is None:
                cleaned[name] = z
        return cleaned


class PagamentoSalarioControleForm(BaseStyledModelForm):
    class Meta:
        model = PagamentoSalarioControle
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={'maxlength': 120}),
        }
        labels = {
            'nome': 'Nome',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()
        self.fields['nome'].required = False
        self.fields['nome'].widget.attrs.setdefault('placeholder', 'Pagamento de salário')


class PagamentoSalarioLinhaForm(BaseStyledModelForm):
    class Meta:
        model = PagamentoSalarioLinha
        fields = ['valor', 'conta_bancaria_empresa']
        widgets = {
            'valor': forms.TextInput(
                attrs={
                    'data-mask': 'br-moeda',
                    'inputmode': 'decimal',
                    'autocomplete': 'off',
                    'maxlength': '20',
                    'placeholder': '0,00',
                    'class': 'text-end',
                }
            ),
            'conta_bancaria_empresa': forms.Select(),
        }
        labels = {
            'valor': 'Valor',
            'conta_bancaria_empresa': 'Banco Empresa',
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()
        self.fields['valor'].required = False
        banco_field = self.fields['conta_bancaria_empresa']
        banco_field.required = False
        banco_field.empty_label = 'Selecione o banco da empresa'
        if empresa:
            banco_field.queryset = banco_field.queryset.filter(empresa=empresa, ativo=True)
        else:
            banco_field.queryset = banco_field.queryset.none()
        if not self.is_bound and self.instance:
            self.initial['valor'] = _decimal_input_ptbr(getattr(self.instance, 'valor', 0))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('valor') is None:
            cleaned['valor'] = Decimal('0')
        return cleaned
