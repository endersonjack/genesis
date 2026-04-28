"""Módulo financeiro: caixas e movimentos (base para fluxo de caixa, boletos e recibos)."""
from __future__ import annotations

import os
from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

from empresas.models import Empresa
from obras.models import Obra
from rh.models import TimeStampedModel


class Caixa(TimeStampedModel):
    """Caixa geral (única por empresa) ou subcaixa (por obra ou nome personalizado)."""

    class Tipo(models.TextChoices):
        GERAL = 'geral', 'Caixa geral'
        OBRA = 'obra', 'Subcaixa de obra'
        PERSONALIZADA = 'personalizada', 'Subcaixa personalizada'

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='caixas_financeiro',
    )
    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices,
        db_index=True,
    )
    obra = models.ForeignKey(
        Obra,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='caixas_financeiro',
        verbose_name='Obra',
        help_text='Obrigatório para subcaixa de obra; vazio para caixa geral ou personalizada.',
    )
    nome = models.CharField(
        max_length=200,
        help_text='Para o caixa geral use «Caixa geral». Subcaixa de obra costuma repetir o nome da obra.',
    )
    ativo = models.BooleanField(
        default=True,
        help_text='Inativas não aparecem em lançamentos novos (histórico preservado).',
    )

    class Meta:
        verbose_name = 'Caixa'
        verbose_name_plural = 'Caixas'
        ordering = ['tipo', 'nome']
        constraints = [
            models.UniqueConstraint(
                fields=('empresa',),
                # Literais: em Meta, o inner class Tipo ainda não está no escopo.
                condition=Q(tipo='geral'),
                name='financeiro_caixa_unica_geral_por_empresa',
            ),
            models.UniqueConstraint(
                fields=('empresa', 'obra'),
                condition=Q(tipo='obra', obra__isnull=False),
                name='financeiro_caixa_unica_obra_por_empresa',
            ),
        ]

    def __str__(self) -> str:
        if self.tipo == self.Tipo.GERAL:
            return f'{self.nome} ({self.empresa})'
        return f'{self.nome} — {self.get_tipo_display()}'

    def clean(self) -> None:
        if self.tipo == self.Tipo.GERAL:
            if self.obra_id:
                raise ValidationError(
                    {'obra': 'Caixa geral não pode estar vinculada a uma obra.'}
                )
        elif self.tipo == self.Tipo.OBRA:
            if not self.obra_id:
                raise ValidationError(
                    {'obra': 'Informe a obra desta subcaixa.'}
                )
            if self.obra and self.obra.empresa_id != self.empresa_id:
                raise ValidationError(
                    {'obra': 'A obra deve pertencer à mesma empresa do caixa.'}
                )
        elif self.tipo == self.Tipo.PERSONALIZADA:
            if self.obra_id:
                raise ValidationError(
                    {
                        'obra': 'Subcaixa personalizada não usa obra; '
                        'use o tipo «Subcaixa de obra».'
                    }
                )

    def saldo_atual(self) -> Decimal:
        """Saldo = entradas − saídas (somatório de movimentos)."""
        agg = self.movimentos.aggregate(
            entradas=Sum('valor', filter=Q(natureza='entrada')),
            saidas=Sum('valor', filter=Q(natureza='saida')),
        )
        e = agg['entradas'] or Decimal('0')
        s = agg['saidas'] or Decimal('0')
        return e - s


class MovimentoCaixa(TimeStampedModel):
    """Lançamento de entrada (recebimento) ou saída (pagamento) em um caixa."""

    class Natureza(models.TextChoices):
        ENTRADA = 'entrada', 'Entrada'
        SAIDA = 'saida', 'Saída'

    class CategoriaOrigem(models.TextChoices):
        RECEBIMENTO_AVULSO = 'rec_avulso', 'Recebimento avulso'
        RECEBIMENTO_CONTRATO = 'rec_contrato', 'Recebimento (contrato)'
        RECEBIMENTO_MEDICAO = 'rec_medicao', 'Recebimento por medição'
        PAGAMENTO_AVULSO = 'pag_avulso', 'Pagamento avulso'
        PAGAMENTO_VISTA = 'pag_vista', 'Pagamento à vista'
        PAGAMENTO_BOLETO = 'pag_boleto', 'Pagamento de boleto'
        TRANSFERENCIA_CAIXA = 'transf_caixa', 'Transferência entre caixas'
        OUTRO = 'outro', 'Outro'

    class MeioPagamento(models.TextChoices):
        PIX = 'pix', 'PIX'
        DINHEIRO = 'dinheiro', 'Dinheiro'
        BOLETO = 'boleto', 'Boleto'
        TRANSFERENCIA = 'transferencia', 'Transferência bancária'
        CARTAO = 'cartao', 'Cartão'
        OUTRO = 'outro', 'Outro'

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='movimentos_caixa',
    )
    caixa = models.ForeignKey(
        Caixa,
        on_delete=models.PROTECT,
        related_name='movimentos',
    )
    natureza = models.CharField(
        max_length=10,
        choices=Natureza.choices,
        db_index=True,
    )
    categoria_origem = models.CharField(
        'Origem',
        max_length=20,
        choices=CategoriaOrigem.choices,
        default=CategoriaOrigem.OUTRO,
        db_index=True,
        help_text='Classificação do lançamento (recibo, contrato, boleto, etc.).',
    )
    meio_pagamento = models.CharField(
        'Meio',
        max_length=20,
        choices=MeioPagamento.choices,
        blank=True,
        help_text='Opcional no MVP; útil para conciliação.',
    )
    valor = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        help_text='Sempre positivo; a natureza define se é entrada ou saída.',
    )
    data = models.DateField('Data', db_index=True)
    descricao = models.CharField(max_length=500)
    observacao = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Movimento de caixa'
        verbose_name_plural = 'Movimentos de caixa'
        ordering = ['-data', '-pk']
        indexes = [
            models.Index(fields=('empresa', 'data')),
            models.Index(fields=('caixa', 'data')),
        ]

    def __str__(self) -> str:
        sinal = '+' if self.natureza == self.Natureza.ENTRADA else '−'
        return f'{self.data} {sinal}{self.valor} — {self.caixa}'

    def clean(self) -> None:
        if self.valor is not None and self.valor <= 0:
            raise ValidationError({'valor': 'Informe um valor maior que zero.'})
        if self.caixa_id and self.empresa_id:
            if self.caixa.empresa_id != self.empresa_id:
                raise ValidationError(
                    {'caixa': 'O caixa deve pertencer à mesma empresa do lançamento.'}
                )
        if self.natureza == self.Natureza.ENTRADA:
            if self.categoria_origem in (
                self.CategoriaOrigem.PAGAMENTO_AVULSO,
                self.CategoriaOrigem.PAGAMENTO_VISTA,
                self.CategoriaOrigem.PAGAMENTO_BOLETO,
            ):
                raise ValidationError(
                    {
                        'categoria_origem': 'Para entrada, use recebimento avulso, '
                        'contrato ou outro.'
                    }
                )
        elif self.natureza == self.Natureza.SAIDA:
            if self.categoria_origem in (
                self.CategoriaOrigem.RECEBIMENTO_AVULSO,
                self.CategoriaOrigem.RECEBIMENTO_CONTRATO,
                self.CategoriaOrigem.RECEBIMENTO_MEDICAO,
            ):
                raise ValidationError(
                    {
                        'categoria_origem': 'Para saída, use pagamento avulso, '
                        'à vista, boleto ou outro.'
                    }
                )


class CategoriaFinanceira(TimeStampedModel):
    class MovimentacaoTipo(models.TextChoices):
        RECEBIMENTO_AVULSO = 'rec_avulso', 'Recebimento'
        RECEBIMENTO_MEDICAO = 'rec_medicao', 'Recebimento por medição'
        PAGAMENTO_NOTA_FISCAL = 'pag_nf', 'Pagamento: Nota Fiscal'
        PAGAMENTO_IMPOSTOS = 'pag_impostos', 'Pagamento: Impostos'
        PAGAMENTO_PESSOAL = 'pag_pessoal', 'Pagamento: Pessoal'
        PAGAMENTO_BANCARIO = 'pag_bancario', 'Pagamento: Bancário'
        PAGAMENTO_ALUGUEIS = 'pag_alugueis', 'Pagamento: Aluguéis'
        PAGAMENTO_VEICULOS = 'pag_veiculos', 'Pagamento: Veículos'
        PAGAMENTO_AVULSO = 'pag_avulso', 'Pagamento: Avulso'
        PAGAMENTO_AVULSO_MENSAL = 'pag_avulso_mensal', 'Pagamento: Avulso Mensal'

    class Tipo(models.TextChoices):
        ENTRADA = 'entrada', 'Entrada (Recebimento)'
        SAIDA = 'saida', 'Saída (Pagamento)'

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='categorias_financeiras',
    )
    tipo = models.CharField(
        max_length=10,
        choices=Tipo.choices,
        db_index=True,
    )
    movimentacao_tipo = models.CharField(
        'Tipo de movimentação',
        max_length=20,
        choices=MovimentacaoTipo.choices,
        db_index=True,
    )
    nome = models.CharField(max_length=200)
    ativo = models.BooleanField(
        default=True,
        help_text='Inativas não aparecem em novos lançamentos (histórico preservado).',
    )

    class Meta:
        verbose_name = 'Categoria financeira'
        verbose_name_plural = 'Categorias financeiras'
        ordering = ['movimentacao_tipo', 'nome']
        constraints = [
            models.UniqueConstraint(
                fields=('empresa', 'movimentacao_tipo', 'nome'),
                name='financeiro_categoria_financeira_unica_por_empresa_mov_tipo_nome',
            )
        ]

    @classmethod
    def tipo_from_movimentacao(cls, movimentacao_tipo: str) -> str:
        if movimentacao_tipo in {
            cls.MovimentacaoTipo.RECEBIMENTO_AVULSO,
            cls.MovimentacaoTipo.RECEBIMENTO_MEDICAO,
        }:
            return cls.Tipo.ENTRADA
        return cls.Tipo.SAIDA

    def save(self, *args, **kwargs):
        if self.movimentacao_tipo:
            self.tipo = self.tipo_from_movimentacao(self.movimentacao_tipo)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.nome} — {self.get_movimentacao_tipo_display()}'


def comprovante_recebimento_upload(instance, filename: str) -> str:
    ext = os.path.splitext(filename)[1]
    sub = instance.__class__.__name__.lower()
    return f'financeiro/comprovantes/{sub}/{uuid4().hex}{ext}'


class RecebimentoAvulso(TimeStampedModel):
    """Recebimento sem contrato/medição — detalhe ligado a um movimento de entrada."""

    class Status(models.TextChoices):
        ABERTO = 'aberto', 'Em aberto'
        PAGO = 'pago', 'Pago'

    movimento = models.OneToOneField(
        MovimentoCaixa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recebimento_avulso',
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='recebimentos_avulsos',
        null=True,
        blank=True,
    )
    caixa = models.ForeignKey(
        Caixa,
        on_delete=models.PROTECT,
        related_name='recebimentos_avulsos',
        null=True,
        blank=True,
    )
    categoria = models.ForeignKey(
        CategoriaFinanceira,
        on_delete=models.PROTECT,
        related_name='recebimentos_avulsos',
        null=True,
        blank=True,
        help_text='Categoria de entrada (recebimento).',
    )
    cliente = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.PROTECT,
        related_name='recebimentos_caixa_avulsos',
        verbose_name='Cliente',
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ABERTO,
        db_index=True,
    )
    data = models.DateField('Data', null=True, blank=True, db_index=True)
    data_pagamento = models.DateField(
        'Data de liquidação',
        null=True,
        blank=True,
        db_index=True,
    )
    valor = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0'))
    impostos = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0'))
    valor_liquido = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0'))
    descricao = models.CharField(max_length=500, blank=True)
    observacao = models.TextField(blank=True)
    comprovante = models.FileField(
        upload_to=comprovante_recebimento_upload,
        blank=True,
        verbose_name='Comprovante',
    )

    class Meta:
        verbose_name = 'Recebimento avulso (caixa)'
        verbose_name_plural = 'Recebimentos avulsos (caixa)'

    def __str__(self) -> str:
        return f'Avulso #{self.pk} — {self.cliente_id}'

    def clean(self) -> None:
        super().clean()
        if self.impostos is not None and self.impostos < 0:
            raise ValidationError({'impostos': 'Valor não pode ser negativo.'})
        if self.valor is not None and self.valor < 0:
            raise ValidationError({'valor': 'Valor não pode ser negativo.'})
        if self.valor is not None and self.impostos is not None and self.impostos >= self.valor:
            raise ValidationError({'impostos': 'Impostos devem ser menores que o valor bruto.'})

    def calcular_valor_liquido(self) -> Decimal:
        return (self.valor or Decimal('0')) - (self.impostos or Decimal('0'))

    def save(self, *args, **kwargs):
        self.valor_liquido = self.calcular_valor_liquido()
        super().save(*args, **kwargs)


class RecebimentoMedicao(TimeStampedModel):
    """Recebimento por contrato/medição — detalhe ligado a um movimento de entrada."""

    class Status(models.TextChoices):
        ABERTO = 'aberto', 'Em aberto'
        PAGO = 'pago', 'Pago'

    movimento = models.OneToOneField(
        MovimentoCaixa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recebimento_medicao',
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='recebimentos_medicao',
        null=True,
        blank=True,
    )
    caixa = models.ForeignKey(
        Caixa,
        on_delete=models.PROTECT,
        related_name='recebimentos_medicao',
        null=True,
        blank=True,
    )
    categoria = models.ForeignKey(
        CategoriaFinanceira,
        on_delete=models.PROTECT,
        related_name='recebimentos_medicao',
        null=True,
        blank=True,
        help_text='Categoria de entrada (recebimento).',
    )
    cliente = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.PROTECT,
        related_name='recebimentos_caixa_medicao',
        verbose_name='Cliente',
    )
    obra = models.ForeignKey(
        Obra,
        on_delete=models.PROTECT,
        related_name='recebimentos_caixa_medicao',
        verbose_name='Obra',
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ABERTO,
        db_index=True,
    )
    data = models.DateField('Data', null=True, blank=True, db_index=True)
    data_pagamento = models.DateField(
        'Data de liquidação',
        null=True,
        blank=True,
        db_index=True,
    )
    valor = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0'))
    impostos = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0'))
    valor_liquido = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0'))
    descricao = models.CharField(max_length=500, blank=True)
    observacao = models.TextField(blank=True)
    medicao_numero = models.CharField(
        'Medição nº',
        max_length=120,
    )
    nota_fiscal_numero = models.CharField(
        'Nº nota fiscal',
        max_length=60,
        blank=True,
        help_text='Opcional. Número da NF-e ou documento fiscal, quando houver.',
    )
    comprovante = models.FileField(
        upload_to=comprovante_recebimento_upload,
        blank=True,
        verbose_name='Comprovante',
    )

    class Meta:
        verbose_name = 'Recebimento por medição (caixa)'
        verbose_name_plural = 'Recebimentos por medição (caixa)'

    def __str__(self) -> str:
        return f'Medição #{self.pk} — {self.medicao_numero}'

    def clean(self) -> None:
        super().clean()
        if self.impostos is not None and self.impostos < 0:
            raise ValidationError({'impostos': 'Valor não pode ser negativo.'})
        if self.valor is not None and self.valor < 0:
            raise ValidationError({'valor': 'Valor não pode ser negativo.'})
        if self.valor is not None and self.impostos is not None and self.impostos >= self.valor:
            raise ValidationError({'impostos': 'Impostos devem ser menores que o valor bruto.'})

    def calcular_valor_liquido(self) -> Decimal:
        return (self.valor or Decimal('0')) - (self.impostos or Decimal('0'))

    def save(self, *args, **kwargs):
        self.valor_liquido = self.calcular_valor_liquido()
        super().save(*args, **kwargs)


class PagamentoNotaFiscal(TimeStampedModel):
    """Pagamento por Nota Fiscal (saída)."""

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='pagamentos_nf',
    )
    fornecedor = models.ForeignKey(
        'fornecedores.Fornecedor',
        on_delete=models.PROTECT,
        related_name='pagamentos_nf',
        verbose_name='Fornecedor',
    )
    numero_nf = models.CharField('Nº NF', max_length=60)
    data_emissao = models.DateField('Data de emissão', default=timezone.localdate, db_index=True)
    caixa = models.ForeignKey(
        Caixa,
        on_delete=models.PROTECT,
        related_name='pagamentos_nf',
        verbose_name='Caixa',
    )
    descricao = models.CharField('Descrição', max_length=500, blank=True)

    class Meta:
        verbose_name = 'Pagamento (nota fiscal)'
        verbose_name_plural = 'Pagamentos (nota fiscal)'
        ordering = ['-data_emissao', '-pk']
        indexes = [
            models.Index(fields=('empresa', 'data_emissao')),
            models.Index(fields=('empresa', 'fornecedor', 'numero_nf')),
        ]

    def __str__(self) -> str:
        return f'NF {self.numero_nf} — {self.fornecedor}'

    def clean(self) -> None:
        if self.caixa_id and self.empresa_id:
            if self.caixa.empresa_id != self.empresa_id:
                raise ValidationError({'caixa': 'O caixa deve pertencer à mesma empresa.'})
        if self.fornecedor_id and self.empresa_id:
            if self.fornecedor.empresa_id != self.empresa_id:
                raise ValidationError(
                    {'fornecedor': 'O fornecedor deve pertencer à mesma empresa.'}
                )

    def total_itens(self) -> Decimal:
        agg = self.itens.aggregate(total=Sum('valor_total'))
        return (agg['total'] or Decimal('0')).quantize(Decimal('0.01'))


class PagamentoNotaFiscalItem(TimeStampedModel):
    class TipoItem(models.TextChoices):
        SERVICO = 'servico', 'Serviço'
        PRODUTO = 'produto', 'Produto'

    pagamento_nf = models.ForeignKey(
        PagamentoNotaFiscal,
        on_delete=models.CASCADE,
        related_name='itens',
    )
    tipo = models.CharField(max_length=10, choices=TipoItem.choices, db_index=True)
    descricao = models.CharField(max_length=500)
    categoria = models.ForeignKey(
        CategoriaFinanceira,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='pagamentos_nf_itens',
        help_text='Categoria de saída (pagamento).',
    )
    quantidade = models.DecimalField(max_digits=16, decimal_places=4, default=Decimal('1'))
    unidade = models.CharField(max_length=30, blank=True)
    valor_unitario = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0'))
    valor_total = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0'))
    caixa = models.ForeignKey(
        Caixa,
        on_delete=models.PROTECT,
        related_name='pagamentos_nf_itens',
        verbose_name='Caixa',
    )

    class Meta:
        verbose_name = 'Item de NF (pagamento)'
        verbose_name_plural = 'Itens de NF (pagamento)'
        ordering = ['pk']

    def clean(self) -> None:
        if self.pagamento_nf_id and self.caixa_id:
            if self.caixa.empresa_id != self.pagamento_nf.empresa_id:
                raise ValidationError({'caixa': 'O caixa deve pertencer à mesma empresa.'})
        if self.categoria_id:
            if (
                self.categoria.movimentacao_tipo
                != CategoriaFinanceira.MovimentacaoTipo.PAGAMENTO_NOTA_FISCAL
            ):
                raise ValidationError(
                    {'categoria': 'Selecione uma categoria de pagamento por nota fiscal.'}
                )
            if self.pagamento_nf_id and self.categoria.empresa_id != self.pagamento_nf.empresa_id:
                raise ValidationError({'categoria': 'Categoria inválida para esta empresa.'})
        if self.quantidade is not None and self.quantidade <= 0:
            raise ValidationError({'quantidade': 'Informe uma quantidade maior que zero.'})
        if self.valor_unitario is not None and self.valor_unitario < 0:
            raise ValidationError({'valor_unitario': 'Valor unitário não pode ser negativo.'})
        if self.valor_total is not None and self.valor_total < 0:
            raise ValidationError({'valor_total': 'Valor total não pode ser negativo.'})


class PagamentoNotaFiscalPagamento(TimeStampedModel):
    class TipoPagamento(models.TextChoices):
        AVISTA = 'avista', 'À vista'
        CREDITO = 'credito', 'Crédito'
        BOLETOS = 'boletos', 'Boletos'

    pagamento_nf = models.OneToOneField(
        PagamentoNotaFiscal,
        on_delete=models.CASCADE,
        related_name='pagamento',
    )
    tipo = models.CharField(max_length=10, choices=TipoPagamento.choices, db_index=True)
    data = models.DateField(default=timezone.localdate, db_index=True)
    valor = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0'))
    acrescimos = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0'))
    descontos = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0'))
    observacao = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Pagamento (dados)'
        verbose_name_plural = 'Pagamentos (dados)'
        ordering = ['-pk']

    def clean(self) -> None:
        if self.pagamento_nf_id:
            if self.data and self.pagamento_nf.data_emissao and self.data < self.pagamento_nf.data_emissao:
                # Permitimos datas anteriores em casos excepcionais? Por ora, validação leve.
                pass
        for fld in ('valor', 'acrescimos', 'descontos'):
            v = getattr(self, fld)
            if v is not None and v < 0:
                raise ValidationError({fld: 'Valor não pode ser negativo.'})

    def total_a_pagar(self) -> Decimal:
        return (self.valor + self.acrescimos - self.descontos).quantize(Decimal('0.01'))


class BoletoPagamento(TimeStampedModel):
    """Boleto gerado a partir de um pagamento por NF (parcelas)."""

    class Status(models.TextChoices):
        RASCUNHO = 'rascunho', 'Rascunho'
        EMITIDO = 'emitido', 'Emitido'
        PAGO = 'pago', 'Pago'
        CANCELADO = 'cancelado', 'Cancelado'

    pagamento_nf = models.ForeignKey(
        PagamentoNotaFiscal,
        on_delete=models.CASCADE,
        related_name='boletos',
    )
    numero_doc = models.CharField('Número doc', max_length=120, db_index=True, blank=True)
    parcela = models.PositiveIntegerField(default=1)
    vencimento = models.DateField(db_index=True)
    valor = models.DecimalField(max_digits=16, decimal_places=2)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.RASCUNHO,
        db_index=True,
    )

    # Campos para futuro controle/relatório e integração com emissão
    banco_codigo = models.CharField(max_length=10, blank=True)
    agencia = models.CharField(max_length=20, blank=True)
    conta = models.CharField(max_length=30, blank=True)
    nosso_numero = models.CharField(max_length=40, blank=True, db_index=True)
    linha_digitavel = models.CharField(max_length=200, blank=True)
    codigo_barras = models.CharField(max_length=200, blank=True)

    data_pagamento = models.DateField(null=True, blank=True, db_index=True)
    acrescimos = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0'))
    descontos = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0'))
    valor_pago = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    observacao = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Boleto'
        verbose_name_plural = 'Boletos'
        ordering = ['vencimento', 'parcela', 'pk']
        constraints = [
            models.UniqueConstraint(
                fields=('pagamento_nf', 'numero_doc'),
                name='financeiro_boleto_numero_doc_unico_por_pagamento_nf',
            )
        ]

    def __str__(self) -> str:
        return f'{self.numero_doc} — {self.get_status_display()}'

    def clean(self) -> None:
        if self.parcela <= 0:
            raise ValidationError({'parcela': 'Parcela deve ser maior que zero.'})
        if self.valor is not None and self.valor <= 0:
            raise ValidationError({'valor': 'Informe um valor maior que zero.'})
        for fld in ('acrescimos', 'descontos'):
            v = getattr(self, fld)
            if v is not None and v < 0:
                raise ValidationError({fld: 'Valor não pode ser negativo.'})
        if self.valor_pago is not None and self.valor_pago < 0:
            raise ValidationError({'valor_pago': 'Valor pago não pode ser negativo.'})
