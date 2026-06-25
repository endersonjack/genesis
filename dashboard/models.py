from django.conf import settings
from django.db import models


class NotaAutoadesiva(models.Model):
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='notas_autoadesivas',
    )
    texto = models.TextField(max_length=1000)
    cor = models.CharField(max_length=7, default='#facc15')
    anexo = models.FileField(upload_to='dashboard/notas_anexos/', blank=True, null=True)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notas_autoadesivas_criadas',
    )
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notas_autoadesivas_recebidas',
    )
    responsaveis = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='notas_autoadesivas_recebidas_multiplas',
    )
    concluida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Nota autoadesiva'
        verbose_name_plural = 'Notas autoadesivas'
        ordering = ['concluida', '-criada_em']

    def __str__(self):
        return self.texto[:60]

    @property
    def tipo_label(self):
        return 'Tarefa' if self.responsavel_id or self.responsaveis.exists() else 'Lembrete'
