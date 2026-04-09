import re
from decimal import Decimal, InvalidOperation

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
    link_maps_embed = models.URLField(
        blank=True,
        max_length=2000,
        verbose_name='Link embed (iframe)',
        help_text='Cole aqui o link do atributo src do iframe do Google Maps.',
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='Latitude',
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='Longitude',
    )

    class Meta:
        verbose_name = 'Local'
        verbose_name_plural = 'Locais'
        ordering = ['nome']
        unique_together = ('empresa', 'nome')

    def __str__(self):
        return self.nome

    @staticmethod
    def parse_lat_lng_from_maps(url: str):
        """
        Tenta extrair coordenadas de URLs do Google Maps.
        Suporta padrões comuns:
        - .../@-5.123456,-35.123456,17z
        - ...?q=-5.123456,-35.123456
        - ...?query=-5.123456,-35.123456
        - ...?ll=-5.123456,-35.123456
        """
        if not url:
            return None, None
        u = str(url).strip()

        # Ex.: https://www.google.com/maps/@-5.7951049,-35.227678,17z
        m = re.search(r'/@(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)', u)
        if not m:
            m = re.search(
                r'[?&](?:q|query|ll)=(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)',
                u,
            )
        # Ex.: iframe embed src (pb): ...!2d-35.227678!3d-5.7951049...
        if not m:
            m = re.search(r'!2d(-?\d+(?:\.\d+)?)!3d(-?\d+(?:\.\d+)?)', u)
        if not m:
            return None, None

        try:
            if '!2d' in (m.group(0) or ''):
                lng = Decimal(m.group(1))
                lat = Decimal(m.group(2))
            else:
                lat = Decimal(m.group(1))
                lng = Decimal(m.group(2))
        except (InvalidOperation, ValueError):
            return None, None

        # Normaliza para 6 casas (compatível com o campo DecimalField)
        try:
            q = Decimal('0.000001')
            lat = lat.quantize(q)
            lng = lng.quantize(q)
        except (InvalidOperation, ValueError):
            return None, None

        if not (Decimal('-90') <= lat <= Decimal('90')):
            return None, None
        if not (Decimal('-180') <= lng <= Decimal('180')):
            return None, None
        return lat, lng


class LocalTrabalhoAtivo(TimeStampedModel):
    """
    Marca um Local como "ativo" na tela de Locais de Trabalho.
    Funcionários podem ser arrastados apenas para Locais ativos.
    """

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='locais_trabalho_ativos',
    )
    local = models.ForeignKey(
        Local,
        on_delete=models.CASCADE,
        related_name='ativacoes_trabalho',
    )

    class Meta:
        verbose_name = 'Local de trabalho ativo'
        verbose_name_plural = 'Locais de trabalho ativos'
        ordering = ['local__nome', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'local'],
                name='unique_local_trabalho_ativo_por_empresa',
            )
        ]

    def __str__(self):
        return f'{self.local} (ativo)'
