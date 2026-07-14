from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


class Alerta(models.Model):
    class Modulo(models.TextChoices):
        GERAL = 'geral', 'Geral'
        RH = 'rh', 'RH'
        FINANCEIRO = 'financeiro', 'Financeiro'
        ESTOQUE = 'estoque', 'Estoque'
        OBRAS = 'obras', 'Obras'
        CLIENTES = 'clientes', 'Clientes'
        FORNECEDORES = 'fornecedores', 'Fornecedores'
        LOCAL = 'local', 'Locais'
        APONTAMENTO = 'apontamento', 'Apontamento'

    class Nivel(models.TextChoices):
        INFO = 'info', 'Informativo'
        ATENCAO = 'atencao', 'Atenção'
        URGENTE = 'urgente', 'Urgente'

    class Status(models.TextChoices):
        ABERTO = 'aberto', 'Aberto'
        LIDO = 'lido', 'Lido'
        RESOLVIDO = 'resolvido', 'Resolvido'
        IGNORADO = 'ignorado', 'Ignorado'

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='alertas',
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alertas',
        help_text='Vazio = alerta visível para todos os usuários da empresa.',
    )
    titulo = models.CharField(max_length=180)
    descricao = models.TextField(blank=True)
    modulo = models.CharField(
        max_length=30,
        choices=Modulo.choices,
        default=Modulo.GERAL,
        db_index=True,
    )
    categoria = models.CharField(
        max_length=80,
        blank=True,
        help_text='Tipo interno: contrato_vencendo, conta_vencendo, exame_vencido etc.',
    )
    nivel = models.CharField(
        max_length=20,
        choices=Nivel.choices,
        default=Nivel.ATENCAO,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ABERTO,
        db_index=True,
    )
    data_alerta = models.DateTimeField(default=timezone.now, db_index=True)
    data_vencimento = models.DateField(null=True, blank=True, db_index=True)
    link_url = models.CharField(max_length=500, blank=True)
    chave = models.CharField(
        max_length=180,
        blank=True,
        help_text='Chave opcional para evitar duplicar alertas automáticos.',
    )

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    objeto_origem = GenericForeignKey('content_type', 'object_id')

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alertas_criados',
    )
    lido_em = models.DateTimeField(null=True, blank=True)
    resolvido_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
        ordering = ['-data_alerta', '-id']
        indexes = [
            models.Index(fields=['empresa', 'status', 'data_alerta']),
            models.Index(fields=['empresa', 'modulo', 'status']),
            models.Index(fields=['empresa', 'chave']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'chave'],
                condition=~models.Q(chave=''),
                name='alerta_empresa_chave_unica_quando_informada',
            ),
        ]

    def __str__(self):
        return self.titulo

    @property
    def pendente(self):
        return self.status in {self.Status.ABERTO, self.Status.LIDO}

    @property
    def icone(self):
        return {
            self.Nivel.INFO: 'bi-info-circle',
            self.Nivel.ATENCAO: 'bi-exclamation-triangle',
            self.Nivel.URGENTE: 'bi-exclamation-octagon',
        }.get(self.nivel, 'bi-bell')

    @property
    def nivel_badge_class(self):
        return {
            self.Nivel.INFO: 'text-bg-primary',
            self.Nivel.ATENCAO: 'text-bg-warning',
            self.Nivel.URGENTE: 'text-bg-danger',
        }.get(self.nivel, 'text-bg-secondary')

    def marcar_lido(self, commit=True):
        if self.status == self.Status.ABERTO:
            self.status = self.Status.LIDO
            self.lido_em = timezone.now()
            if commit:
                self.save(update_fields=['status', 'lido_em', 'atualizado_em'])
        return self

    def marcar_resolvido(self, commit=True):
        self.status = self.Status.RESOLVIDO
        now = timezone.now()
        if not self.lido_em:
            self.lido_em = now
        self.resolvido_em = now
        if commit:
            self.save(update_fields=['status', 'lido_em', 'resolvido_em', 'atualizado_em'])
        return self
