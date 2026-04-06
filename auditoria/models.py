from django.conf import settings
from django.db import models


class RegistroAuditoria(models.Model):
    """Trilha de ações no contexto de uma empresa (via views + registrar_auditoria)."""

    ACAO_CHOICES = [
        ('create', 'Criação'),
        ('update', 'Alteração'),
        ('delete', 'Exclusão'),
        ('export', 'Exportação'),
        ('other', 'Outro'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='registros_auditoria',
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registros_auditoria',
    )
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)
    acao = models.CharField(max_length=20, choices=ACAO_CHOICES, db_index=True)
    modulo = models.CharField(
        max_length=80,
        blank=True,
        help_text='Identificador curto do app ou área (ex.: empresas, rh).',
    )
    resumo = models.CharField(max_length=255)
    detalhes = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Registro de auditoria'
        verbose_name_plural = 'Registros de auditoria'
        indexes = [
            models.Index(fields=['empresa', 'criado_em']),
        ]

    def __str__(self):
        return f'{self.get_acao_display()} — {self.resumo[:60]}'
