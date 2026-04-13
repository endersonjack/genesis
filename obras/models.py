from django.db import models

from clientes.models import Cliente
from empresas.models import Empresa
from rh.models import TimeStampedModel


class Obra(TimeStampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='obras',
    )
    nome = models.CharField('Nome da obra', max_length=200)
    contratante = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='obras',
        verbose_name='Contratante',
    )
    objeto = models.TextField('Objeto', blank=True)
    endereco = models.CharField('Endereço', max_length=500, blank=True)
    cno = models.CharField(
        'CNO',
        max_length=30,
        blank=True,
        help_text='Cadastro Nacional de Obras (quando aplicável).',
    )
    valor = models.DecimalField(
        'Valor (R$)',
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
    )
    secretaria = models.CharField('Secretaria', max_length=200, blank=True)
    gestor = models.CharField('Gestor', max_length=200, blank=True)
    fiscal = models.CharField('Fiscal', max_length=200, blank=True)
    data_inicio = models.DateField('Início', null=True, blank=True)
    prazo = models.CharField(
        'Prazo',
        max_length=120,
        blank=True,
        help_text='Ex.: 6 meses, 12 meses…',
    )
    data_fim = models.DateField('Fim', null=True, blank=True)

    class Meta:
        verbose_name = 'Obra'
        verbose_name_plural = 'Obras'
        ordering = ['nome']

    def __str__(self):
        return self.nome
