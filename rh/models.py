from django.db import models
from empresas.models import Empresa


class TimeStampedModel(models.Model):
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Cargo(TimeStampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='cargos'
    )
    nome = models.CharField(max_length=120)

    class Meta:
        verbose_name = 'Cargo'
        verbose_name_plural = 'Cargos'
        ordering = ['nome']
        unique_together = ('empresa', 'nome')

    def __str__(self):
        return self.nome


class TipoContrato(TimeStampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='tipos_contrato'
    )
    nome = models.CharField(max_length=100)

    class Meta:
        verbose_name = 'Tipo de Contrato'
        verbose_name_plural = 'Tipos de Contrato'
        ordering = ['nome']
        unique_together = ('empresa', 'nome')

    def __str__(self):
        return self.nome


class Lotacao(TimeStampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='lotacoes'
    )
    nome = models.CharField(max_length=150)

    class Meta:
        verbose_name = 'Lotação'
        verbose_name_plural = 'Lotações'
        ordering = ['nome']
        unique_together = ('empresa', 'nome')

    def __str__(self):
        return self.nome


class Banco(TimeStampedModel):
    nome = models.CharField(max_length=120)
    codigo = models.CharField(max_length=10, blank=True)

    class Meta:
        verbose_name = 'Banco'
        verbose_name_plural = 'Bancos'
        ordering = ['nome']

    def __str__(self):
        if self.codigo:
            return f'{self.codigo} - {self.nome}'
        return self.nome


class Funcionario(TimeStampedModel):
    SEXO_CHOICES = (
        ('M', 'Masculino'),
        ('F', 'Feminino'),
        ('O', 'Outro'),
    )

    ESTADO_CIVIL_CHOICES = (
        ('solteiro', 'Solteiro(a)'),
        ('casado', 'Casado(a)'),
        ('divorciado', 'Divorciado(a)'),
        ('viuvo', 'Viúvo(a)'),
        ('uniao_estavel', 'União estável'),
    )

    STATUS_CHOICES = (
        ('admitido', 'Admitido'),
        ('ativo', 'Ativo'),
        ('afastado', 'Afastado'),
        ('ferias', 'Férias'),
        ('demitido', 'Demitido'),
    )

    TIPO_DEMISSAO_CHOICES = (
        ('', '---------'),
        ('sem_justa_causa', 'Sem justa causa'),
        ('com_justa_causa', 'Com justa causa'),
        ('pedido_demissao', 'Pedido de demissão'),
        ('termino_contrato', 'Término de contrato'),
        ('acordo', 'Acordo'),
        ('aposentadoria', 'Aposentadoria'),
        ('obito', 'Óbito'),
        ('outro', 'Outro'),
    )

    TIPO_CONTA_CHOICES = (
        ('', '---------'),
        ('corrente', 'Conta Corrente'),
        ('poupanca', 'Conta Poupança'),
        ('salario', 'Conta Salário'),
    )

    CHAVE_PIX_CHOICES = (
        ('', '---------'),
        ('cpf', 'CPF'),
        ('email', 'E-mail'),
        ('telefone', 'Telefone'),
        ('aleatoria', 'Chave Aleatória'),
    )

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='funcionarios'
    )

    matricula = models.CharField(max_length=30, blank=True)
    foto = models.ImageField(
        upload_to='funcionarios/fotos/',
        null=True,
        blank=True
    )

    nome = models.CharField(max_length=200)
    cpf = models.CharField(max_length=14)
    rg = models.CharField(max_length=20, blank=True)
    cnh = models.CharField(max_length=20, blank=True)
    categoria_cnh = models.CharField(max_length=10, blank=True)
    nacionalidade = models.CharField(max_length=60, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)
    endereco_completo = models.CharField(max_length=255, blank=True)
    telefone_1 = models.CharField(max_length=20, blank=True)
    telefone_2 = models.CharField(max_length=20, blank=True)
    estado_civil = models.CharField(
        max_length=20,
        choices=ESTADO_CIVIL_CHOICES,
        blank=True
    )
    nome_mae = models.CharField(max_length=200, blank=True)
    nome_pai = models.CharField(max_length=200, blank=True)
    sexo = models.CharField(
        max_length=1,
        choices=SEXO_CHOICES,
        blank=True
    )

    tipo_contrato = models.ForeignKey(
        TipoContrato,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='funcionarios'
    )
    data_admissao = models.DateField(null=True, blank=True)
    inicio_prorrogacao = models.DateField(null=True, blank=True)
    fim_prorrogacao = models.DateField(null=True, blank=True)
    situacao_atual = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='admitido'
    )
    inicio_afastamento = models.DateField(null=True, blank=True)
    fim_afastamento = models.DateField(null=True, blank=True)
    data_demissao = models.DateField(null=True, blank=True)
    tipo_demissao = models.CharField(
        max_length=30,
        choices=TIPO_DEMISSAO_CHOICES,
        blank=True
    )

    cargo = models.ForeignKey(
        Cargo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='funcionarios'
    )
    lotacao = models.ForeignKey(
        Lotacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='funcionarios'
    )

    salario = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    adicional = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    data_ultimo_exame = models.DateField(null=True, blank=True)
    responsavel = models.CharField(max_length=150, blank=True)

    banco = models.ForeignKey(
        Banco,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='funcionarios'
    )
    agencia = models.CharField(max_length=20, blank=True)
    tipo_conta = models.CharField(
        max_length=20,
        choices=TIPO_CONTA_CHOICES,
        blank=True
    )
    operacao = models.CharField(max_length=20, blank=True)
    numero_conta = models.CharField(max_length=30, blank=True)
    tipo_pix = models.CharField(
        max_length=20,
        choices=CHAVE_PIX_CHOICES,
        blank=True
    )
    pix = models.CharField(max_length=150, blank=True)

    e_social = models.CharField(max_length=100, blank=True)
    analfabeto = models.BooleanField(default=False)
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Funcionário'
        verbose_name_plural = 'Funcionários'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'matricula'],
                name='unique_matricula_por_empresa'
            ),
            models.UniqueConstraint(
                fields=['empresa', 'cpf'],
                name='unique_cpf_por_empresa'
            ),
        ]

    def __str__(self):
        return self.nome


class Dependente(TimeStampedModel):
    PARENTESCO_CHOICES = (
        ('filho', 'Filho(a)'),
        ('conjuge', 'Cônjuge'),
        ('enteado', 'Enteado(a)'),
        ('outro', 'Outro'),
    )

    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        related_name='dependentes'
    )
    nome = models.CharField(max_length=200)
    data_nascimento = models.DateField(null=True, blank=True)
    cpf = models.CharField(max_length=14, blank=True)
    parentesco = models.CharField(
        max_length=20,
        choices=PARENTESCO_CHOICES,
        default='filho'
    )

    class Meta:
        verbose_name = 'Dependente'
        verbose_name_plural = 'Dependentes'
        ordering = ['nome']

    def __str__(self):
        return f'{self.nome} - {self.funcionario.nome}'