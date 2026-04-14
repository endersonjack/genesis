from django.db import models

from empresas.models import Empresa
from rh.models import TimeStampedModel

from .upload_paths import item_imagem_upload, item_qrcode_upload


class CategoriaItem(TimeStampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='categorias_item',
    )
    nome = models.CharField(max_length=120)

    class Meta:
        verbose_name = 'Categoria de item'
        verbose_name_plural = 'Categorias de itens'
        ordering = ['nome']
        unique_together = ('empresa', 'nome')

    def __str__(self):
        return self.nome


class CategoriaFerramenta(TimeStampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='categorias_ferramenta',
    )
    nome = models.CharField(max_length=120)

    class Meta:
        verbose_name = 'Categoria de ferramenta'
        verbose_name_plural = 'Categorias de ferramentas'
        ordering = ['nome']
        unique_together = ('empresa', 'nome')

    def __str__(self):
        return self.nome


class UnidadeMedida(TimeStampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='unidades_medida',
    )
    abreviada = models.CharField(
        'Medida abreviada',
        max_length=32,
        help_text='Ex.: Kg, m, UN',
    )
    completa = models.CharField(
        'Medida completa',
        max_length=120,
        help_text='Ex.: Quilograma, Metro, Unidade',
    )

    class Meta:
        verbose_name = 'Unidade de medida'
        verbose_name_plural = 'Unidades de medida'
        ordering = ['abreviada']
        unique_together = ('empresa', 'abreviada')

    def __str__(self):
        return self.abreviada


class Item(TimeStampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='itens_estoque',
    )
    descricao = models.CharField(max_length=500)
    marca = models.CharField(max_length=120, blank=True)
    categoria = models.ForeignKey(
        CategoriaItem,
        on_delete=models.PROTECT,
        related_name='itens',
    )
    peso = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        help_text='Opcional. Ex.: peso por unidade (kg).',
    )
    unidade_medida = models.ForeignKey(
        UnidadeMedida,
        on_delete=models.PROTECT,
        related_name='itens',
    )
    preco = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    fornecedor = models.ForeignKey(
        'fornecedores.Fornecedor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itens_estoque',
    )
    quantidade_minima = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0,
        blank=True,
        help_text='Quantidade mínima no estoque (alertas futuros).',
    )
    quantidade_estoque = models.DecimalField(
        'Quantidade em estoque',
        max_digits=14,
        decimal_places=4,
        default=0,
        help_text='Saldo atual. Movimentações futuras alterarão este valor.',
    )
    ativo = models.BooleanField(
        default=True,
        help_text='Itens inativos não entram em movimentação nem nas buscas operacionais.',
    )
    qrcode_imagem = models.ImageField(
        upload_to=item_qrcode_upload,
        blank=True,
        null=True,
        verbose_name='QR Code',
        help_text='Imagem do QR Code gerada ao salvar o item (leitor 2D nas telas de estoque).',
    )

    class Meta:
        verbose_name = 'Item'
        verbose_name_plural = 'Itens'
        ordering = ['descricao']

    def __str__(self):
        return self.descricao[:80]


class ItemImagem(TimeStampedModel):
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='imagens',
    )
    imagem = models.ImageField(upload_to=item_imagem_upload)
    ordem = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Imagem do item'
        verbose_name_plural = 'Imagens do item'
        ordering = ['ordem', 'pk']

    def __str__(self):
        return f'Imagem #{self.pk} — {self.item_id}'


class RequisicaoEstoque(TimeStampedModel):
    class Status(models.TextChoices):
        ATIVA = 'ativa', 'Ativa'
        CANCELADA = 'cancelada', 'Cancelada'

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='requisicoes_estoque',
    )
    status = models.CharField(
        'Situação',
        max_length=20,
        choices=Status.choices,
        default=Status.ATIVA,
        db_index=True,
        help_text=(
            'No app, só é possível cancelar (com devolução ao estoque). '
            'Reativar ou alterar situação manualmente no Admin não ajusta o estoque.'
        ),
    )
    solicitante = models.ForeignKey(
        'rh.Funcionario',
        on_delete=models.PROTECT,
        related_name='requisicoes_estoque_solicitadas',
    )
    local = models.ForeignKey(
        'local.Local',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisicoes_estoque',
    )
    obra = models.ForeignKey(
        'obras.Obra',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisicoes_estoque',
    )
    almoxarife = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisicoes_estoque_almoxarife',
    )

    class Meta:
        verbose_name = 'Requisição de estoque'
        verbose_name_plural = 'Requisições de estoque'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['empresa', 'criado_em']),
            models.Index(fields=['empresa', 'status', 'criado_em']),
        ]

    def __str__(self):
        return f'Requisição #{self.pk} — {self.criado_em:%d/%m/%Y %H:%M}'

    @property
    def is_ativa(self) -> bool:
        return self.status == self.Status.ATIVA


class RequisicaoEstoqueItem(models.Model):
    requisicao = models.ForeignKey(
        RequisicaoEstoque,
        on_delete=models.CASCADE,
        related_name='itens',
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='requisicoes_itens',
    )
    quantidade = models.DecimalField(max_digits=14, decimal_places=4, default=0)

    class Meta:
        verbose_name = 'Item requisitado'
        verbose_name_plural = 'Itens requisitados'
        ordering = ['pk']
        constraints = [
            models.UniqueConstraint(
                fields=['requisicao', 'item'],
                name='unique_item_por_requisicao',
            )
        ]

    def __str__(self):
        return f'{self.item} × {self.quantidade}'
