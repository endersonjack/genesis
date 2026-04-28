import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0005_categoria_nos_recebimentos'),
    ]

    operations = [
        migrations.CreateModel(
            name='PagamentoNotaFiscal',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('numero_nf', models.CharField(max_length=60, verbose_name='Nº NF')),
                (
                    'data_emissao',
                    models.DateField(
                        db_index=True,
                        default=django.utils.timezone.localdate,
                        verbose_name='Data de emissão',
                    ),
                ),
                ('descricao', models.CharField(max_length=500, verbose_name='Descrição')),
                (
                    'caixa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='pagamentos_nf',
                        to='financeiro.caixa',
                        verbose_name='Caixa',
                    ),
                ),
                (
                    'empresa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='pagamentos_nf',
                        to='empresas.empresa',
                    ),
                ),
                (
                    'fornecedor',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='pagamentos_nf',
                        to='fornecedores.fornecedor',
                        verbose_name='Fornecedor',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Pagamento (nota fiscal)',
                'verbose_name_plural': 'Pagamentos (nota fiscal)',
                'ordering': ['-data_emissao', '-pk'],
            },
        ),
        migrations.CreateModel(
            name='PagamentoNotaFiscalPagamento',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                (
                    'tipo',
                    models.CharField(
                        choices=[('avista', 'À vista'), ('credito', 'Crédito'), ('boletos', 'Boletos')],
                        db_index=True,
                        max_length=10,
                    ),
                ),
                (
                    'data',
                    models.DateField(
                        db_index=True,
                        default=django.utils.timezone.localdate,
                    ),
                ),
                ('valor', models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ('acrescimos', models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ('descontos', models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ('observacao', models.TextField(blank=True)),
                (
                    'pagamento_nf',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='pagamento',
                        to='financeiro.pagamentonotafiscal',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Pagamento (dados)',
                'verbose_name_plural': 'Pagamentos (dados)',
                'ordering': ['-pk'],
            },
        ),
        migrations.CreateModel(
            name='PagamentoNotaFiscalItem',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                (
                    'tipo',
                    models.CharField(
                        choices=[('servico', 'Serviço'), ('produto', 'Produto')],
                        db_index=True,
                        max_length=10,
                    ),
                ),
                ('descricao', models.CharField(max_length=500)),
                ('quantidade', models.DecimalField(decimal_places=4, default=1, max_digits=16)),
                ('unidade', models.CharField(blank=True, max_length=30)),
                ('valor_unitario', models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ('valor_total', models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                (
                    'caixa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='pagamentos_nf_itens',
                        to='financeiro.caixa',
                        verbose_name='Caixa',
                    ),
                ),
                (
                    'categoria',
                    models.ForeignKey(
                        blank=True,
                        help_text='Categoria de saída (pagamento).',
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='pagamentos_nf_itens',
                        to='financeiro.categoriafinanceira',
                    ),
                ),
                (
                    'pagamento_nf',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='itens',
                        to='financeiro.pagamentonotafiscal',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Item de NF (pagamento)',
                'verbose_name_plural': 'Itens de NF (pagamento)',
                'ordering': ['pk'],
            },
        ),
        migrations.CreateModel(
            name='BoletoPagamento',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('numero_doc', models.CharField(db_index=True, max_length=120, verbose_name='Número doc')),
                ('parcela', models.PositiveIntegerField(default=1)),
                ('vencimento', models.DateField(db_index=True)),
                ('valor', models.DecimalField(decimal_places=2, max_digits=16)),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('rascunho', 'Rascunho'),
                            ('emitido', 'Emitido'),
                            ('pago', 'Pago'),
                            ('cancelado', 'Cancelado'),
                        ],
                        db_index=True,
                        default='rascunho',
                        max_length=12,
                    ),
                ),
                ('banco_codigo', models.CharField(blank=True, max_length=10)),
                ('agencia', models.CharField(blank=True, max_length=20)),
                ('conta', models.CharField(blank=True, max_length=30)),
                ('nosso_numero', models.CharField(blank=True, db_index=True, max_length=40)),
                ('linha_digitavel', models.CharField(blank=True, max_length=200)),
                ('codigo_barras', models.CharField(blank=True, max_length=200)),
                ('data_pagamento', models.DateField(blank=True, db_index=True, null=True)),
                ('valor_pago', models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True)),
                ('observacao', models.TextField(blank=True)),
                (
                    'pagamento_nf',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='boletos',
                        to='financeiro.pagamentonotafiscal',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Boleto',
                'verbose_name_plural': 'Boletos',
                'ordering': ['vencimento', 'parcela', 'pk'],
            },
        ),
        migrations.AddIndex(
            model_name='pagamentonotafiscal',
            index=models.Index(fields=['empresa', 'data_emissao'], name='financeiro__empresa_5bfb85_idx'),
        ),
        migrations.AddIndex(
            model_name='pagamentonotafiscal',
            index=models.Index(fields=['empresa', 'fornecedor', 'numero_nf'], name='financeiro__empresa_0e9a72_idx'),
        ),
        migrations.AddConstraint(
            model_name='boletopagamento',
            constraint=models.UniqueConstraint(
                fields=('pagamento_nf', 'numero_doc'),
                name='financeiro_boleto_numero_doc_unico_por_pagamento_nf',
            ),
        ),
    ]

