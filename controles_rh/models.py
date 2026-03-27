from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


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

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.titulo:
            self.titulo = self.get_titulo_padrao()
        self.full_clean()
        super().save(*args, **kwargs)


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

    def clean(self):
        errors = {}

        if self.valor_pagar is not None and self.valor_pagar < 0:
            errors['valor_pagar'] = 'O valor a pagar não pode ser negativo.'

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

        self.full_clean()
        super().save(*args, **kwargs)