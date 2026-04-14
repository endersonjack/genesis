from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    nome_completo = models.CharField(max_length=255, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    foto = models.ImageField(
        'Foto do perfil',
        upload_to='usuarios/fotos/',
        blank=True,
        null=True,
    )

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
    editar_empresas = models.BooleanField(
        'Editar empresas (preferências)',
        default=False,
        help_text='Permite editar as preferências da empresa (dados, logo e configurações).',
    )
    rh = models.BooleanField(
        'RH',
        default=False,
        help_text='Libera acesso ao módulo de Recursos Humanos nesta empresa.',
    )
    estoque = models.BooleanField(
        'Estoque',
        default=False,
        help_text='Libera acesso ao módulo de Estoque nesta empresa.',
    )
    financeiro = models.BooleanField(
        'Financeiro',
        default=False,
        help_text='Libera acesso ao módulo Financeiro nesta empresa.',
    )
    clientes = models.BooleanField(
        'Clientes',
        default=True,
        help_text='Libera acesso ao cadastro de Clientes nesta empresa.',
    )
    fornecedores = models.BooleanField(
        'Fornecedores',
        default=True,
        help_text='Libera acesso ao cadastro de Fornecedores nesta empresa.',
    )
    locais = models.BooleanField(
        'Locais',
        default=True,
        help_text='Libera acesso ao cadastro de Locais nesta empresa.',
    )
    obras = models.BooleanField(
        'Obras',
        default=True,
        help_text='Libera acesso ao cadastro de Obras nesta empresa.',
    )
    auditoria_total = models.BooleanField(
        'Auditoria total',
        default=False,
        help_text='Permite visualizar a auditoria de todos os usuários na empresa.',
    )
    auditoria_sua = models.BooleanField(
        'Auditoria sua',
        default=True,
        help_text='Permite visualizar a auditoria apenas das próprias ações na empresa.',
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
        if self.editar_empresas is None:
            self.editar_empresas = False
        if self.rh is None:
            self.rh = False
        if self.estoque is None:
            self.estoque = False
        if self.financeiro is None:
            self.financeiro = False
        if self.clientes is None:
            self.clientes = True
        if self.fornecedores is None:
            self.fornecedores = True
        if self.locais is None:
            self.locais = True
        if self.obras is None:
            self.obras = True
        if self.auditoria_total is None:
            self.auditoria_total = False
        if self.auditoria_sua is None:
            self.auditoria_sua = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.usuario} - {self.empresa}'