from django.db import models

from empresas.models import Empresa
from rh.models import TimeStampedModel


class Local(TimeStampedModel):
    """
    Ponto de trabalho / endereço físico (mapa).
    No futuro: funcionários poderão referenciar um Local.
    """

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='locais',
    )
    nome = models.CharField(
        max_length=150,
        verbose_name='Local',
        help_text='Nome identificador (ex.: obra, filial, setor físico).',
    )
    endereco = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Endereço',
    )
    link_maps = models.URLField(
        blank=True,
        max_length=2000,
        verbose_name='Link (mapas)',
        help_text='URL do Google Maps ou outro serviço de localização.',
    )

    class Meta:
        verbose_name = 'Local'
        verbose_name_plural = 'Locais'
        ordering = ['nome']
        unique_together = ('empresa', 'nome')

    def __str__(self):
        return self.nome
