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
        ('afastado', 'Afastado'),
        ('ferias', 'Férias'),
        ('demitido', 'Demitido'),
        ('inativo', 'Inativo'),
        ('terceirizado', 'Terceirizado'),
        ('outro', 'Outro'),
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

    TIPO_AVISO_CHOICES = (
        ('', '---------'),
        ('trabalhado', 'Trabalhado'),
        ('indenizado', 'Indenizado'),
        ('dispensado', 'Dispensado do cumprimento'),
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

    # identificação
    matricula = models.CharField(max_length=30, blank=True)
    foto = models.ImageField(
        upload_to='funcionarios/fotos/',
        null=True,
        blank=True
    )

    # dados pessoais
    nome = models.CharField(max_length=200)
    cpf = models.CharField(max_length=14)
    pis = models.CharField('PIS', max_length=20, blank=True)
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

    # admissão / vínculo
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

    salario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        blank=True
    )
    adicional = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        blank=True
    )

    recebe_vale_transporte = models.BooleanField(default=False)
    valor_vale_transporte = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        default=0
    )
    contribuinte_sindical = models.BooleanField(default=False)
    recebe_salario_familia = models.BooleanField(
        default=False,
        verbose_name='Recebe salário família',
        help_text='Salário família (INSS). Pode ser usado em relatórios e integrações futuras.',
    )

    situacao_atual = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='admitido'
    )

    data_ultimo_exame = models.DateField(null=True, blank=True)
    responsavel = models.CharField(max_length=150, blank=True)

    # demissão
    data_demissao = models.DateField(null=True, blank=True)
    tipo_demissao = models.CharField(
        max_length=30,
        choices=TIPO_DEMISSAO_CHOICES,
        blank=True
    )
    tipo_aviso = models.CharField(
        max_length=20,
        choices=TIPO_AVISO_CHOICES,
        blank=True
    )
    data_inicio_aviso = models.DateField(null=True, blank=True)
    data_fim_aviso = models.DateField(null=True, blank=True)
    anexo_aviso = models.FileField(
        upload_to='rh/avisos_demissao/',
        null=True,
        blank=True
    )
    precisa_exame_demissional = models.BooleanField(default=False)
    rescisao_assinada = models.FileField(
        upload_to='rh/rescisoes/',
        null=True,
        blank=True
    )
    observacoes_demissao = models.TextField(blank=True)

    # dados bancários
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

    # outros
    e_social = models.CharField(max_length=100, blank=True)
    analfabeto = models.BooleanField(default=False)
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Funcionário'
        verbose_name_plural = 'Funcionários'
        ordering = ['nome']
        constraints = []
        

    def __str__(self):
        return self.nome

    @property
    def deve_fazer_exame_demissional(self):
        if self.data_admissao and self.data_demissao:
            return (self.data_demissao - self.data_admissao).days > 90
        return False

    def save(self, *args, **kwargs):
        if self.data_admissao and self.data_demissao:
            self.precisa_exame_demissional = (
                (self.data_demissao - self.data_admissao).days > 90
            )
        else:
            self.precisa_exame_demissional = False

        if self.data_demissao:
            # Regra do projeto: demitido vira desativado (não aparece por padrão).
            self.situacao_atual = 'inativo'
        elif self.situacao_atual in ('demitido', 'inativo'):
            self.situacao_atual = 'admitido'
        
        super().save(*args, **kwargs)


    @property
    def classe_resumo_status(self):
        if self.situacao_atual in ['demitido', 'inativo']:
            return 'top-summary-danger'
        elif self.situacao_atual == 'afastado':
            return 'top-summary-warning'
        elif self.situacao_atual == 'ferias':
            return 'top-summary-success'
        return 'top-summary-default'

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


class FeriasFuncionario(TimeStampedModel):
    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        related_name='ferias'
    )
    periodo_aquisitivo_inicio = models.DateField(null=True, blank=True)
    periodo_aquisitivo_fim = models.DateField(null=True, blank=True)
    gozo_inicio = models.DateField(null=True, blank=True)
    gozo_fim = models.DateField(null=True, blank=True)
    teve_abono_pecuniario = models.BooleanField(default=False)
    dias_abono_pecuniario = models.PositiveIntegerField(null=True, blank=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Férias'
        verbose_name_plural = 'Férias'
        ordering = ['-gozo_inicio', '-periodo_aquisitivo_inicio']

    def __str__(self):
        return f'Férias de {self.funcionario.nome}'


class AfastamentoFuncionario(TimeStampedModel):
    TIPO_AFASTAMENTO_CHOICES = (
        ('doenca', 'Doença'),
        ('acidente_trabalho', 'Acidente de trabalho'),
        ('licenca_maternidade', 'Licença maternidade'),
        ('licenca_paternidade', 'Licença paternidade'),
        ('auxilio_doenca', 'Auxílio-doença'),
        ('suspensao', 'Suspensão'),
        ('outro', 'Outro'),
    )

    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        related_name='afastamentos'
    )
    tipo = models.CharField(
        max_length=30,
        choices=TIPO_AFASTAMENTO_CHOICES
    )
    data_afastamento = models.DateField()
    previsao_retorno = models.DateField(null=True, blank=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Afastamento'
        verbose_name_plural = 'Afastamentos'
        ordering = ['-data_afastamento']

    def __str__(self):
        return f'{self.funcionario.nome} - {self.get_tipo_display()}'
    

class ASOFuncionario(TimeStampedModel):
    TIPO_ASO_CHOICES = (
        ('admissional', 'Admissional'),
        ('periodico', 'Periódico'),
        ('demissional', 'Demissional'),
        ('retorno_trabalho', 'Retorno ao trabalho'),
        ('mudanca_funcao', 'Mudança de função'),
        ('outro', 'Outro'),
    )

    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        related_name='asos'
    )
    tipo = models.CharField(max_length=30, choices=TIPO_ASO_CHOICES)
    data = models.DateField()
    anexo = models.FileField(
        upload_to='rh/saude/aso/',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'ASO'
        verbose_name_plural = 'ASOs'
        ordering = ['-data']

    def __str__(self):
        return f'{self.funcionario.nome} - {self.get_tipo_display()}'
    
class CertificadoFuncionario(TimeStampedModel):
    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        related_name='certificados'
    )
    tipo = models.CharField(max_length=120)
    data = models.DateField(null=True, blank=True)
    anexo = models.FileField(
        upload_to='rh/saude/certificados/',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Certificado'
        verbose_name_plural = 'Certificados'
        ordering = ['-data', 'tipo']

    def __str__(self):
        return f'{self.funcionario.nome} - {self.tipo}'
    
class PCMSOFuncionario(TimeStampedModel):
    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        related_name='pcmso_registros'
    )
    data_vencimento = models.DateField()
    anexo = models.FileField(
        upload_to='rh/saude/pcmso/',
        null=True,
        blank=True
    )
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Registro de PCMSO'
        verbose_name_plural = 'Registros de PCMSO'
        ordering = ['-data_vencimento']

    def __str__(self):
        return f'PCMSO - {self.funcionario.nome}'
    
class AtestadoLicencaFuncionario(TimeStampedModel):
    TIPO_CHOICES = (
        ('atestado_medico', 'Atestado médico'),
        ('licenca_medica', 'Licença médica'),
        ('licenca_maternidade', 'Licença maternidade'),
        ('licenca_paternidade', 'Licença paternidade'),
        ('licenca_nao_remunerada', 'Licença não remunerada'),
        ('outro', 'Outro'),
    )

    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        related_name='atestados_licencas'
    )
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    data = models.DateField()
    periodo_inicio = models.DateField(null=True, blank=True)
    periodo_fim = models.DateField(null=True, blank=True)
    anexo = models.FileField(
        upload_to='rh/saude/atestados_licencas/',
        null=True,
        blank=True
    )
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Atestado / Licença'
        verbose_name_plural = 'Atestados / Licenças'
        ordering = ['-data', '-periodo_inicio']

    def __str__(self):
        return f'{self.funcionario.nome} - {self.get_tipo_display()}'

class OcorrenciaSaudeFuncionario(TimeStampedModel):
    TIPO_CHOICES = (
        ('acidente', 'Acidente'),
        ('doenca', 'Doença'),
    )

    ORIGEM_CHOICES = (
        ('trabalho', 'No trabalho'),
        ('percurso', 'No percurso'),
        ('outro', 'Outro'),
    )

    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        related_name='ocorrencias_saude'
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descricao = models.TextField()
    origem = models.CharField(
        max_length=20,
        choices=ORIGEM_CHOICES,
        blank=True
    )
    data = models.DateField(null=True, blank=True)
    anexo = models.FileField(
        upload_to='rh/saude/ocorrencias/',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Ocorrência de Saúde'
        verbose_name_plural = 'Ocorrências de Saúde'
        ordering = ['-data', '-criado_em']

    def __str__(self):
        return f'{self.funcionario.nome} - {self.get_tipo_display()}'
    

class AnexoAvulsoFuncionario(TimeStampedModel):
    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        related_name='anexos_avulsos'
    )
    titulo = models.CharField(max_length=150)
    data_documento = models.DateField(null=True, blank=True)
    descricao = models.TextField(blank=True)
    arquivo = models.FileField(upload_to='rh/anexos_avulsos/')
    origem_label = models.CharField(max_length=80, default='Anexo avulso', editable=False)

    class Meta:
        verbose_name = 'Anexo avulso'
        verbose_name_plural = 'Anexos avulsos'
        ordering = ['-data_documento', '-criado_em']

    def __str__(self):
        return f'{self.funcionario.nome} - {self.titulo}'
    

from django.conf import settings
from django.db import models
from django.utils import timezone


class HistoricoAlteracao(models.Model):
    ACAO_CHOICES = [
        ('create', 'Criou'),
        ('update', 'Alterou'),
        ('delete', 'Excluiu'),
    ]

    funcionario = models.ForeignKey(
        'Funcionario',
        on_delete=models.CASCADE,
        related_name='historicos'
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    data_hora = models.DateTimeField(default=timezone.now)
    acao = models.CharField(max_length=10, choices=ACAO_CHOICES)
    modelo = models.CharField(max_length=100, blank=True)
    registro_id = models.CharField(max_length=50, blank=True)
    titulo = models.CharField(max_length=255, blank=True)
    descricao = models.TextField(blank=True)
    alteracoes = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-data_hora']

    def __str__(self):
        return f'{self.titulo or "Histórico"} - {self.funcionario}'
    
class LembreteRH(TimeStampedModel):
    TIPO_CHOICES = (
        ('geral', 'Geral'),
        ('documento', 'Documento'),
        ('financeiro', 'Financeiro'),
        ('rh', 'RH'),
        ('saude', 'Saúde'),
        ('feriado', 'Feriado'),
        ('outro', 'Outro'),
    )

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='lembretes_rh'
    )
    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lembretes_rh'
    )
    titulo = models.CharField(max_length=160)
    descricao = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='geral')
    data = models.DateField()
    cor = models.CharField(max_length=20, blank=True, default='')
    concluido = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Lembrete RH'
        verbose_name_plural = 'Lembretes RH'
        ordering = ['data', 'titulo']

    def __str__(self):
        return f'{self.titulo} - {self.data:%d/%m/%Y}'
    

