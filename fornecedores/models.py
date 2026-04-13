from django.db import models

from empresas.models import Empresa
from rh.models import Banco, TimeStampedModel


class CategoriaFornecedor(TimeStampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='categorias_fornecedor',
    )
    nome = models.CharField(max_length=120)

    class Meta:
        verbose_name = 'Categoria de fornecedor'
        verbose_name_plural = 'Categorias de fornecedor'
        ordering = ['nome']
        unique_together = ('empresa', 'nome')

    def __str__(self):
        return self.nome


class Fornecedor(TimeStampedModel):
    TIPO_PESSOA_CHOICES = (
        ('PF', 'Pessoa Física'),
        ('PJ', 'Pessoa Jurídica'),
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
        related_name='fornecedores',
    )
    tipo = models.CharField(
        max_length=2,
        choices=TIPO_PESSOA_CHOICES,
        default='PJ',
    )
    categoria = models.ForeignKey(
        CategoriaFornecedor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fornecedores',
    )
    cpf_cnpj = models.CharField(
        'CPF/CNPJ',
        max_length=14,
        help_text='Apenas números (11 ou 14 dígitos).',
    )
    nome = models.CharField(max_length=200)
    razao_social = models.CharField(max_length=200, blank=True)
    endereco = models.CharField('Endereço', max_length=500, blank=True)
    telefone_loja = models.CharField('Telefone (loja)', max_length=20, blank=True)
    telefone_financeiro = models.CharField('Telefone (financeiro)', max_length=20, blank=True)
    contato_financeiro = models.CharField(
        'Contato financeiro',
        max_length=150,
        blank=True,
        help_text='Nome da pessoa no financeiro.',
    )
    email = models.EmailField('E-mail', blank=True)

    banco = models.ForeignKey(
        Banco,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fornecedores',
    )
    agencia = models.CharField(max_length=20, blank=True)
    tipo_conta = models.CharField(
        max_length=20,
        choices=TIPO_CONTA_CHOICES,
        blank=True,
    )
    operacao = models.CharField(max_length=20, blank=True)
    numero_conta = models.CharField(max_length=30, blank=True)
    tipo_pix = models.CharField(
        max_length=20,
        choices=CHAVE_PIX_CHOICES,
        blank=True,
    )
    pix = models.CharField(max_length=150, blank=True)

    class Meta:
        verbose_name = 'Fornecedor'
        verbose_name_plural = 'Fornecedores'
        ordering = ['nome']
        unique_together = ('empresa', 'cpf_cnpj')

    @property
    def cpf_cnpj_formatado(self) -> str:
        from .utils_doc import display_cpf_cnpj

        return display_cpf_cnpj(self.cpf_cnpj or '', self.tipo) or '—'

    def __str__(self):
        return self.nome
