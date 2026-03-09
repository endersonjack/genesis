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
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'empresa')
        verbose_name = 'Vínculo Usuário/Empresa'
        verbose_name_plural = 'Vínculos Usuário/Empresa'

    def __str__(self):
        return f'{self.usuario} - {self.empresa}'