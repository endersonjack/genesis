from django.db import models

from empresas.models import Empresa
from rh.models import TimeStampedModel


class Cliente(TimeStampedModel):
    TIPO_CHOICES = (
        ('PF', 'Pessoa Física'),
        ('PJ', 'Pessoa Jurídica'),
        ('AP', 'Administração Pública'),
    )

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='clientes',
    )
    tipo = models.CharField(
        max_length=2,
        choices=TIPO_CHOICES,
        default='PJ',
    )
    nome = models.CharField(max_length=200)
    cpf_cnpj = models.CharField(
        'CPF/CNPJ',
        max_length=14,
        blank=True,
        help_text='Apenas números (11 ou 14 dígitos), conforme o tipo.',
    )
    razao_social = models.CharField(max_length=200, blank=True)
    endereco = models.CharField('Endereço', max_length=500, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField('E-mail', blank=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(
                fields=('empresa', 'cpf_cnpj'),
                condition=~models.Q(cpf_cnpj=''),
                name='cliente_empresa_cpf_cnpj_uniq_nonempty',
            ),
        ]

    @property
    def cpf_cnpj_formatado(self) -> str:
        from fornecedores.utils_doc import display_cpf_cnpj

        return display_cpf_cnpj(self.cpf_cnpj or '', self.tipo) or '—'

    def __str__(self):
        return self.nome
