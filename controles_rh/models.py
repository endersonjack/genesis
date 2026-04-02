from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F


STATUS_PAGAMENTO_VT_CHOICES = [
    ('em_pagamento', 'Em pagamento'),
    ('pago_completo', 'Pago completo'),
]

STATUS_ENTREGA_CESTA_CHOICES = [
    ('falta_entregar', 'Falta entregar'),
    ('entregue_totalmente', 'Entregue totalmente'),
]


def _status_pagamento_vt_de_itens(itens_qs):
    """
    Considera apenas itens ativos com valor a pagar > 0.
    Se algum ainda tiver saldo (valor a pagar > valor pago), retorna em_pagamento.
    """
    pendentes = itens_qs.filter(ativo=True).filter(valor_pagar__gt=F('valor_pago'))
    if pendentes.exists():
        return 'em_pagamento'
    return 'pago_completo'


def _status_entrega_cesta_de_itens(itens_qs):
    """
    Considera apenas itens ativos.
    Se não houver linhas ativas, considera entregue totalmente.
    Se algum ativo ainda não marcou recebimento, falta entregar.
    """
    ativos = itens_qs.filter(ativo=True)
    if not ativos.exists():
        return 'entregue_totalmente'
    if ativos.filter(recebido=False).exists():
        return 'falta_entregar'
    return 'entregue_totalmente'


class Competencia(models.Model):
    """
    Representa a competência mensal do módulo de Gestão RH.
    Ex.: 03/2026
    """

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='competencias_rh'
    )
    mes = models.PositiveSmallIntegerField(verbose_name='Mês')
    ano = models.PositiveSmallIntegerField(verbose_name='Ano')

    titulo = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='Título'
    )

    fechada = models.BooleanField(
        default=False,
        verbose_name='Fechada'
    )

    observacao = models.TextField(
        blank=True,
        verbose_name='Observação'
    )

    vt_calculo_automatico = models.BooleanField(
        default=True,
        verbose_name='Status VT automático',
        help_text='Quando ativo, o status de pagamento do VT é calculado pelas tabelas e itens.',
    )
    vt_status_manual = models.CharField(
        max_length=20,
        choices=STATUS_PAGAMENTO_VT_CHOICES,
        blank=True,
        null=True,
        verbose_name='Status VT manual',
        help_text='Usado apenas quando o status automático está desligado.',
    )

    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Competência'
        verbose_name_plural = 'Competências'
        ordering = ['-ano', '-mes', '-id']
        unique_together = ('empresa', 'ano', 'mes')
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'mes', 'ano'],
                name='unique_competencia_por_empresa'
            )
        ]

    def __str__(self):
        return self.referencia

    @property
    def referencia(self):
        return f'{self.mes:02d}/{self.ano}'

    def get_titulo_padrao(self):
        meses = {
            1: 'Janeiro',
            2: 'Fevereiro',
            3: 'Março',
            4: 'Abril',
            5: 'Maio',
            6: 'Junho',
            7: 'Julho',
            8: 'Agosto',
            9: 'Setembro',
            10: 'Outubro',
            11: 'Novembro',
            12: 'Dezembro',
        }
        return f'{meses.get(self.mes, "Competência")}/{self.ano}'

    def clean(self):
        errors = {}

        if not 1 <= self.mes <= 12:
            errors['mes'] = 'Informe um mês entre 1 e 12.'

        if self.ano < 2000 or self.ano > 2100:
            errors['ano'] = 'Informe um ano válido.'

        if not self.vt_calculo_automatico and not self.vt_status_manual:
            errors['vt_status_manual'] = 'Informe o status manual ou reative o cálculo automático.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.titulo:
            self.titulo = self.get_titulo_padrao()
        self.full_clean()
        super().save(*args, **kwargs)

    def _vt_status_agregado_tabelas(self):
        tabelas = self.tabelas_vt.all()
        if not tabelas.exists():
            return 'pago_completo'
        for tabela in tabelas:
            if tabela.vt_status_efetivo == 'em_pagamento':
                return 'em_pagamento'
        return 'pago_completo'

    @property
    def vt_status_efetivo(self):
        if self.vt_calculo_automatico:
            return self._vt_status_agregado_tabelas()
        return self.vt_status_manual or 'em_pagamento'

    @property
    def vt_status_efetivo_label(self):
        return dict(STATUS_PAGAMENTO_VT_CHOICES).get(self.vt_status_efetivo, self.vt_status_efetivo)


class ValeTransporteTabela(models.Model):
    """
    Representa uma tabela/grupo de VT dentro de uma competência.
    Ex.:
    - VT Escritório
    - VT Obra A
    - VT Equipe Externa
    """

    competencia = models.ForeignKey(
        Competencia,
        on_delete=models.CASCADE,
        related_name='tabelas_vt'
    )

    nome = models.CharField(
        max_length=120,
        verbose_name='Nome da tabela'
    )

    descricao = models.TextField(
        blank=True,
        verbose_name='Descrição'
    )

    ordem = models.PositiveIntegerField(
        default=0,
        verbose_name='Ordem'
    )

    ativa = models.BooleanField(
        default=True,
        verbose_name='Ativa'
    )

    fechada = models.BooleanField(
        default=False,
        verbose_name='Fechada'
    )

    vt_calculo_automatico = models.BooleanField(
        default=True,
        verbose_name='Status pagamento automático',
        help_text='Quando ativo, o status é calculado pelos itens (valores a pagar x pagos).',
    )
    vt_status_manual = models.CharField(
        max_length=20,
        choices=STATUS_PAGAMENTO_VT_CHOICES,
        blank=True,
        null=True,
        verbose_name='Status pagamento manual',
        help_text='Usado apenas quando o cálculo automático está desligado.',
    )

    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tabela de Vale Transporte'
        verbose_name_plural = 'Tabelas de Vale Transporte'
        ordering = ['ordem', 'nome', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['competencia', 'nome'],
                name='unique_tabela_vt_por_competencia'
            )
        ]

    def __str__(self):
        return f'{self.nome} - {self.competencia.referencia}'

    @property
    def empresa(self):
        return self.competencia.empresa

    @property
    def total_itens(self):
        return self.itens.count()

    @property
    def total_valor(self):
        total = self.itens.aggregate(total=models.Sum('valor_pagar'))['total']
        return total or Decimal('0.00')

    @property
    def total_valor_pago(self):
        total = self.itens.aggregate(total=models.Sum('valor_pago'))['total']
        return total or Decimal('0.00')

    def clean(self):
        errors = {}
        if not self.vt_calculo_automatico and not self.vt_status_manual:
            errors['vt_status_manual'] = 'Informe o status manual ou reative o cálculo automático.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def vt_status_efetivo(self):
        if self.vt_calculo_automatico:
            return _status_pagamento_vt_de_itens(self.itens.all())
        return self.vt_status_manual or 'em_pagamento'

    @property
    def vt_status_efetivo_label(self):
        return dict(STATUS_PAGAMENTO_VT_CHOICES).get(self.vt_status_efetivo, self.vt_status_efetivo)


class ValeTransporteItem(models.Model):
    """
    Cada linha da tabela de VT.
    """

    TIPO_PIX_CHOICES = [
        ('cpf', 'CPF'),
        ('telefone', 'Telefone'),
        ('email', 'E-mail'),
        ('aleatoria', 'Chave aleatória'),
    ]

    tabela = models.ForeignKey(
        ValeTransporteTabela,
        on_delete=models.CASCADE,
        related_name='itens'
    )

    funcionario = models.ForeignKey(
        'rh.Funcionario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itens_vale_transporte'
    )

    nome = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Nome'
    )

    funcao = models.CharField(
        max_length=120,
        blank=True,
        verbose_name='Função'
    )

    endereco = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Endereço'
    )

    valor_pagar = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Valor a pagar'
    )

    valor_base = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Valor base',
        help_text='Valor de referência (espelha o valor a pagar na prática).',
    )

    valor_pago = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Valor pago'
    )

    data_pagamento = models.DateField(
        blank=True,
        null=True,
        verbose_name='Data de pagamento',
    )

    pix = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Chave Pix'
    )

    tipo_pix = models.CharField(
        max_length=20,
        choices=TIPO_PIX_CHOICES,
        blank=True,
        verbose_name='Tipo Pix'
    )

    banco = models.CharField(
        max_length=120,
        blank=True,
        verbose_name='Banco'
    )

    observacao = models.TextField(
        blank=True,
        verbose_name='Observação'
    )

    ordem = models.PositiveIntegerField(
        default=0,
        verbose_name='Ordem'
    )

    ativo = models.BooleanField(
        default=True,
        verbose_name='Ativo'
    )

    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Item de Vale Transporte'
        verbose_name_plural = 'Itens de Vale Transporte'
        ordering = ['ordem', 'nome', 'id']

    def __str__(self):
        return self.nome_exibicao

    @property
    def nome_exibicao(self):
        if self.nome:
            return self.nome
        if self.funcionario:
            return self.funcionario.nome
        return 'Sem nome'

    @property
    def empresa(self):
        return self.tabela.competencia.empresa

    @property
    def competencia(self):
        return self.tabela.competencia

    @property
    def saldo(self):
        vp = self.valor_pagar or Decimal('0')
        pp = self.valor_pago or Decimal('0')
        return vp - pp

    @property
    def classe_linha_pagamento(self):
        if not self.ativo:
            return ''
        vp = self.valor_pagar or Decimal('0')
        if vp <= 0:
            return ''
        if self.saldo <= 0:
            return 'vt-row-pago-completo'
        return 'vt-row-pago-parcial'

    def clean(self):
        errors = {}

        if self.valor_pagar is not None and self.valor_pagar < 0:
            errors['valor_pagar'] = 'O valor a pagar não pode ser negativo.'

        if self.valor_pago is not None and self.valor_pago < 0:
            errors['valor_pago'] = 'O valor pago não pode ser negativo.'

        if self.valor_base is not None and self.valor_base < 0:
            errors['valor_base'] = 'O valor base não pode ser negativo.'

        if self.funcionario_id and self.tabela_id:
            funcionario_empresa_id = getattr(self.funcionario, 'empresa_id', None)
            tabela_empresa_id = self.tabela.competencia.empresa_id

            if funcionario_empresa_id and funcionario_empresa_id != tabela_empresa_id:
                errors['funcionario'] = 'O funcionário deve pertencer à mesma empresa da competência.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.funcionario:
            if not self.nome:
                self.nome = getattr(self.funcionario, 'nome', '') or self.nome
            if not self.funcao:
                cargo = getattr(self.funcionario, 'cargo', None)
                self.funcao = str(cargo) if cargo else self.funcao
            if not self.endereco:
                self.endereco = getattr(self.funcionario, 'endereco_completo', '') or self.endereco

        vp = self.valor_pagar if self.valor_pagar is not None else Decimal('0')
        self.valor_base = vp

        self.full_clean()
        super().save(*args, **kwargs)


class CestaBasicaLista(models.Model):
    """
    Recibo / controle de Cesta Básica por competência.
    Pode haver várias listas na mesma competência (ex.: obras, equipes).
    """

    competencia = models.ForeignKey(
        Competencia,
        on_delete=models.CASCADE,
        related_name='cestas_basicas',
    )

    titulo = models.CharField(
        max_length=120,
        blank=True,
        verbose_name='Título interno',
        help_text='Opcional. Identificação na lista de controles.',
    )

    texto_declaracao = models.TextField(
        blank=True,
        verbose_name='Texto da declaração',
        help_text='Vazio = texto padrão com o nome da empresa.',
    )

    data_emissao_recibo = models.DateField(
        null=True,
        blank=True,
        verbose_name='Data no rodapé do recibo',
    )

    local_emissao = models.CharField(
        max_length=120,
        blank=True,
        default='PARNAMIRIM - RN',
        verbose_name='Local (cidade/UF)',
    )

    observacao = models.TextField(blank=True, verbose_name='Observação interna')

    ativa = models.BooleanField(default=True, verbose_name='Ativa')

    cb_calculo_automatico = models.BooleanField(
        default=True,
        verbose_name='Status de entrega automático',
        help_text='Quando ativo, o status é calculado pelos checkboxes “Recebeu” nas linhas.',
    )
    cb_status_manual = models.CharField(
        max_length=30,
        choices=STATUS_ENTREGA_CESTA_CHOICES,
        blank=True,
        null=True,
        verbose_name='Status de entrega manual',
        help_text='Usado apenas quando o status automático está desligado.',
    )

    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Lista de Cesta Básica'
        verbose_name_plural = 'Listas de Cesta Básica'
        ordering = ['data_criacao', 'id']

    def __str__(self):
        return f'{self.nome_exibicao} — {self.competencia.referencia}'

    @property
    def nome_exibicao(self):
        return (self.titulo or '').strip() or 'Cesta Básica'

    def clean(self):
        errors = {}
        if not self.cb_calculo_automatico and not self.cb_status_manual:
            errors['cb_status_manual'] = (
                'Informe o status manual ou reative o cálculo automático.'
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def cb_status_efetivo(self):
        if self.cb_calculo_automatico:
            return _status_entrega_cesta_de_itens(self.itens.all())
        return self.cb_status_manual or 'falta_entregar'

    @property
    def cb_status_efetivo_label(self):
        return dict(STATUS_ENTREGA_CESTA_CHOICES).get(
            self.cb_status_efetivo, self.cb_status_efetivo
        )


class CestaBasicaItem(models.Model):
    """Linha do recibo de cesta básica."""

    lista = models.ForeignKey(
        CestaBasicaLista,
        on_delete=models.CASCADE,
        related_name='itens',
    )

    funcionario = models.ForeignKey(
        'rh.Funcionario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itens_cesta_basica',
    )

    nome = models.CharField(max_length=150, blank=True, verbose_name='Empregado')

    funcao = models.CharField(max_length=120, blank=True, verbose_name='Função')

    lotacao = models.CharField(
        max_length=120,
        blank=True,
        verbose_name='Lotação',
    )

    ordem = models.PositiveIntegerField(default=0, verbose_name='Ordem')

    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    recebido = models.BooleanField(
        default=False,
        verbose_name='Recebeu',
        help_text='Marque quando a cesta já foi entregue a este empregado.',
    )

    data_recebimento = models.DateField(
        null=True,
        blank=True,
        verbose_name='Data de recebimento',
    )

    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Item de Cesta Básica'
        verbose_name_plural = 'Itens de Cesta Básica'
        ordering = ['ordem', 'nome', 'id']

    def __str__(self):
        return self.nome_exibicao

    @property
    def nome_exibicao(self):
        if self.nome:
            return self.nome
        if self.funcionario:
            return self.funcionario.nome
        return 'Sem nome'

    def clean(self):
        errors = {}
        if self.funcionario_id and self.lista_id:
            fe = getattr(self.funcionario, 'empresa_id', None)
            le = self.lista.competencia.empresa_id
            if fe and fe != le:
                errors['funcionario'] = 'O funcionário deve pertencer à mesma empresa da competência.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.funcionario:
            if not self.nome:
                self.nome = getattr(self.funcionario, 'nome', '') or self.nome
            if not self.funcao:
                cargo = getattr(self.funcionario, 'cargo', None)
                self.funcao = str(cargo) if cargo else self.funcao
            if not (self.lotacao or '').strip():
                lot = getattr(self.funcionario, 'lotacao', None)
                if lot:
                    self.lotacao = lot.nome
        self.full_clean()
        super().save(*args, **kwargs)
