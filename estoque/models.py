from django.conf import settings
from django.db import models

from empresas.models import Empresa
from rh.models import TimeStampedModel

from .upload_paths import (
    ferramenta_imagem_upload,
    ferramenta_qrcode_upload,
    item_imagem_upload,
    item_qrcode_upload,
)


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

    @property
    def imagem_listagem(self):
        """Imagem usada em miniaturas: a marcada como padrão, senão a primeira por ordem."""
        chosen = None
        first = None
        for im in self.imagens.all():
            if first is None:
                first = im
            if im.padrao:
                chosen = im
                break
        return chosen if chosen is not None else first


class ItemImagem(TimeStampedModel):
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='imagens',
    )
    imagem = models.ImageField(upload_to=item_imagem_upload)
    ordem = models.PositiveSmallIntegerField(default=0)
    padrao = models.BooleanField(
        'Padrão para visualização',
        default=False,
        help_text='Imagem exibida nas listagens e buscas quando houver mais de uma.',
    )

    class Meta:
        verbose_name = 'Imagem do item'
        verbose_name_plural = 'Imagens do item'
        ordering = ['ordem', 'pk']

    def __str__(self):
        return f'Imagem #{self.pk} — {self.item_id}'


class Ferramenta(TimeStampedModel):
    class SituacaoCautela(models.TextChoices):
        LIVRE = 'livre', 'Livre'
        OCUPADA = 'ocupada', 'Ocupada'

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='ferramentas',
    )
    descricao = models.CharField(max_length=500)
    marca = models.CharField(max_length=120, blank=True)
    categoria = models.ForeignKey(
        CategoriaFerramenta,
        on_delete=models.PROTECT,
        related_name='ferramentas',
    )
    cor = models.CharField(max_length=64, blank=True)
    tamanho = models.CharField(max_length=64, blank=True)
    codigo_numeracao = models.CharField(
        'Código / numeração',
        max_length=64,
        blank=True,
        help_text='Identificador interno ou de patrimônio (opcional).',
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
        related_name='ferramentas_estoque',
    )
    ativo = models.BooleanField(
        default=True,
        help_text='Ferramentas inativas não aparecem nas buscas principais.',
    )
    qrcode_imagem = models.ImageField(
        upload_to=ferramenta_qrcode_upload,
        blank=True,
        null=True,
        verbose_name='QR Code',
        help_text='Imagem do QR Code gerada ao salvar (leitor 2D nas telas de estoque).',
    )
    observacoes = models.TextField('Obs.', blank=True)
    situacao_cautela = models.CharField(
        'Situação na cautela',
        max_length=10,
        choices=SituacaoCautela.choices,
        default=SituacaoCautela.LIVRE,
        db_index=True,
        help_text='Ferramenta fica OCUPADA enquanto estiver em cautela ativa e volta a LIVRE quando for entregue.',
    )

    class Meta:
        verbose_name = 'Ferramenta'
        verbose_name_plural = 'Ferramentas'
        ordering = ['descricao']

    def __str__(self):
        return self.descricao[:80]

    @property
    def imagem_listagem(self):
        """Imagem usada em miniaturas: a marcada como padrão, senão a primeira por ordem."""
        chosen = None
        first = None
        for im in self.imagens.all():
            if first is None:
                first = im
            if im.padrao:
                chosen = im
                break
        return chosen if chosen is not None else first


class FerramentaImagem(TimeStampedModel):
    ferramenta = models.ForeignKey(
        Ferramenta,
        on_delete=models.CASCADE,
        related_name='imagens',
    )
    imagem = models.ImageField(upload_to=ferramenta_imagem_upload)
    ordem = models.PositiveSmallIntegerField(default=0)
    padrao = models.BooleanField(
        'Padrão para visualização',
        default=False,
        help_text='Imagem exibida nas listagens e buscas quando houver mais de uma.',
    )

    class Meta:
        verbose_name = 'Imagem da ferramenta'
        verbose_name_plural = 'Imagens da ferramenta'
        ordering = ['ordem', 'pk']

    def __str__(self):
        return f'Imagem #{self.pk} — {self.ferramenta_id}'


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


class RascunhoNovaCautela(TimeStampedModel):
    """Rascunho do formulário Nova cautela (por usuário e empresa). Excluído ao salvar a cautela."""

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='rascunhos_nova_cautela',
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rascunhos_nova_cautela_estoque',
    )
    dados = models.JSONField(
        default=dict,
        help_text='JSON com chaves form (campos do formulário) e items (ferramentas).',
    )

    class Meta:
        verbose_name = 'Rascunho de nova cautela'
        verbose_name_plural = 'Rascunhos de nova cautela'
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'usuario'],
                name='uniq_rascunho_nova_cautela_empresa_usuario',
            ),
        ]

    def __str__(self):
        return f'Rascunho cautela — {self.usuario_id} / empresa {self.empresa_id}'


class Cautela(TimeStampedModel):
    class Situacao(models.TextChoices):
        ATIVA = 'ativa', 'Ativa'
        INATIVA = 'inativa', 'Inativa'

    class Entrega(models.TextChoices):
        NAO = 'nao', 'Não'
        PARCIAL = 'parcial', 'Parcial'
        TOTAL = 'total', 'Total'

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='cautelas_ferramentas',
    )
    funcionario = models.ForeignKey(
        'rh.Funcionario',
        on_delete=models.PROTECT,
        related_name='cautelas_ferramentas',
    )
    ferramentas = models.ManyToManyField(
        Ferramenta,
        blank=True,
        related_name='cautelas_ferramentas',
    )
    almoxarife = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cautelas_ferramentas_almoxarife',
    )
    data_inicio_cautela = models.DateField('Data início da cautela')
    data_fim = models.DateField('Data fim', null=True, blank=True)
    local = models.ForeignKey(
        'local.Local',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cautelas_ferramentas',
    )
    obra = models.ForeignKey(
        'obras.Obra',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cautelas_ferramentas',
    )
    situacao = models.CharField(
        'Situação',
        max_length=10,
        choices=Situacao.choices,
        default=Situacao.ATIVA,
        db_index=True,
    )
    entrega = models.CharField(
        'Entrega',
        max_length=10,
        choices=Entrega.choices,
        default=Entrega.NAO,
        db_index=True,
        help_text='Indica o andamento da devolução das ferramentas.',
    )
    observacoes = models.TextField('Obs.', blank=True)

    class Meta:
        verbose_name = 'Cautela de ferramentas'
        verbose_name_plural = 'Cautelas de ferramentas'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['empresa', 'situacao']),
            models.Index(fields=['empresa', 'entrega']),
        ]

    def __str__(self):
        return f'Cautela #{self.pk} — {self.funcionario}'

    @property
    def data_registro(self):
        # Alias para o requisito “Data de registro” (usa `criado_em` do TimeStampedModel).
        return self.criado_em


class MotivoDevolucaoCautela(TimeStampedModel):
    """Catálogo de motivos (cadastro via Admin)."""

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='motivos_devolucao_cautela',
    )
    nome = models.CharField(max_length=200)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Motivo da devolução (cautela)'
        verbose_name_plural = 'Motivos da devolução (cautela)'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'nome'],
                name='uniq_motivo_devolucao_cautela_empresa_nome',
            ),
        ]

    def __str__(self):
        return self.nome


class SituacaoFerramentasPosDevolucao(TimeStampedModel):
    """Catálogo de situação das ferramentas após devolução (cadastro via Admin)."""

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='situacoes_ferramentas_pos_devolucao',
    )
    nome = models.CharField(max_length=200)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Situação da(s) ferramentas (pós-devolução)'
        verbose_name_plural = 'Situações da(s) ferramentas (pós-devolução)'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'nome'],
                name='uniq_situacao_ferr_pos_dev_empresa_nome',
            ),
        ]

    def __str__(self):
        return self.nome


class Entrega_Cautela(TimeStampedModel):
    class Tipo(models.TextChoices):
        PARCIAL = 'parcial', 'Parcial'
        COMPLETA = 'completa', 'Completa'

    cautela = models.ForeignKey(
        Cautela,
        on_delete=models.CASCADE,
        related_name='entregas',
    )
    tipo = models.CharField(
        'Tipo',
        max_length=10,
        choices=Tipo.choices,
        db_index=True,
    )
    data_entrega = models.DateField('Data da entrega')
    observacoes = models.TextField('Obs.', blank=True)
    motivo = models.ForeignKey(
        MotivoDevolucaoCautela,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='entregas_cautela',
    )
    situacao_ferramentas = models.ForeignKey(
        SituacaoFerramentasPosDevolucao,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='entregas_cautela',
        verbose_name='Situação da(s) ferramentas',
    )
    ferramentas_devolvidas = models.ManyToManyField(
        Ferramenta,
        blank=True,
        related_name='entregas_cautela_devolucoes',
        verbose_name='Ferramentas devolvidas neste registro',
    )

    class Meta:
        verbose_name = 'Entrega / devolução de cautela'
        verbose_name_plural = 'Entregas / devoluções de cautelas'
        ordering = ['-data_entrega', '-criado_em']

    def __str__(self):
        return (
            f'{self.cautela} — {self.get_tipo_display()} em '
            f'{self.data_entrega:%d/%m/%Y}'
        )
