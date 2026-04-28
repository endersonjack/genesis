import django.db.models.deletion
from django.db import migrations, models

import financeiro.models


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0002_cliente_cpf_cnpj'),
        ('financeiro', '0001_initial'),
        ('obras', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecebimentoAvulso',
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
                    'comprovante',
                    models.FileField(
                        blank=True,
                        upload_to=financeiro.models.comprovante_recebimento_upload,
                        verbose_name='Comprovante',
                    ),
                ),
                (
                    'cliente',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='recebimentos_caixa_avulsos',
                        to='clientes.cliente',
                        verbose_name='Cliente',
                    ),
                ),
                (
                    'movimento',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='recebimento_avulso',
                        to='financeiro.movimentocaixa',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Recebimento avulso (caixa)',
                'verbose_name_plural': 'Recebimentos avulsos (caixa)',
            },
        ),
        migrations.CreateModel(
            name='RecebimentoMedicao',
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
                    'medicao_numero',
                    models.CharField(max_length=120, verbose_name='Medição nº'),
                ),
                (
                    'comprovante',
                    models.FileField(
                        blank=True,
                        upload_to=financeiro.models.comprovante_recebimento_upload,
                        verbose_name='Comprovante',
                    ),
                ),
                (
                    'cliente',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='recebimentos_caixa_medicao',
                        to='clientes.cliente',
                        verbose_name='Cliente',
                    ),
                ),
                (
                    'movimento',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='recebimento_medicao',
                        to='financeiro.movimentocaixa',
                    ),
                ),
                (
                    'obra',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='recebimentos_caixa_medicao',
                        to='obras.obra',
                        verbose_name='Obra',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Recebimento por medição (caixa)',
                'verbose_name_plural': 'Recebimentos por medição (caixa)',
            },
        ),
    ]
