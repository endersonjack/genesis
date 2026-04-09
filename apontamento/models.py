from django.conf import settings
from django.db import models

from empresas.models import Empresa
from local.models import Local
from rh.models import Funcionario, TimeStampedModel


class StatusApontamento(models.TextChoices):
    PENDENTE = 'pendente', 'Pendente'
    FINALIZADO = 'finalizado', 'Finalizado'
    ARQUIVADO = 'arquivado', 'Arquivado'


class ApontamentoFalta(TimeStampedModel):
    """
    Registro de falta feito pelo apontador em campo.
    Não substitui FaltaFuncionario (cadastro oficial do RH).
    """

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='apontamentos_falta',
    )
    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        related_name='apontamentos_falta',
    )
    data = models.DateField()
    motivo = models.CharField(max_length=500)
    observacao = models.TextField(blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='apontamentos_falta_registrados',
    )
    status = models.CharField(
        max_length=20,
        choices=StatusApontamento.choices,
        default=StatusApontamento.PENDENTE,
        db_index=True,
    )

    class Meta:
        verbose_name = 'Falta (apontamento)'
        verbose_name_plural = 'Faltas (apontamento)'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.funcionario} — {self.data}'


class ApontamentoObservacaoLocal(TimeStampedModel):
    """Observação sobre o local de trabalho registrada pelo apontador."""

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='apontamentos_observacao_local',
    )
    local = models.ForeignKey(
        Local,
        on_delete=models.CASCADE,
        related_name='apontamentos_observacao',
    )
    data = models.DateField()
    texto = models.TextField()
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='apontamentos_observacao_registrados',
    )
    status = models.CharField(
        max_length=20,
        choices=StatusApontamento.choices,
        default=StatusApontamento.PENDENTE,
        db_index=True,
    )

    class Meta:
        verbose_name = 'Observação de local (apontamento)'
        verbose_name_plural = 'Observações de local (apontamento)'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.local} — {self.data}'
