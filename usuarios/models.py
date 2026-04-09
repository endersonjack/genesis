from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    nome_completo = models.CharField(max_length=255, blank=True)
    telefone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.nome_completo or self.username


class UsuarioEmpresa(models.Model):
    usuario = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.CASCADE,
        related_name='vinculos_empresa'
    )
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='usuarios_vinculados'
    )
    ativo = models.BooleanField(default=True)
    admin_empresa = models.BooleanField(default=False)
    apontador = models.BooleanField(
        'Apontador',
        default=False,
        help_text='Libera o módulo Apontamento (campo) nesta empresa: faltas e observações de local.',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'empresa')
        verbose_name = 'Vínculo Usuário/Empresa'
        verbose_name_plural = 'Vínculos Usuário/Empresa'

    def save(self, *args, **kwargs):
        # Evita INSERT com NULL se algum fluxo não preencher o campo (admin/ORM).
        if self.apontador is None:
            self.apontador = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.usuario} - {self.empresa}'