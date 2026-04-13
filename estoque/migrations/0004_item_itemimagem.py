import django.db.models.deletion
from django.db import migrations, models

import estoque.upload_paths


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0004_empresa_logo'),
        ('fornecedores', '0001_initial'),
        ('estoque', '0003_unidademedida_abreviada_completa'),
    ]

    operations = [
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('descricao', models.CharField(max_length=500)),
                ('marca', models.CharField(blank=True, max_length=120)),
                (
                    'peso',
                    models.DecimalField(
                        blank=True,
                        decimal_places=3,
                        help_text='Opcional. Ex.: peso por unidade (kg).',
                        max_digits=12,
                        null=True,
                    ),
                ),
                ('preco', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                (
                    'quantidade_minima',
                    models.DecimalField(
                        blank=True,
                        decimal_places=4,
                        default=0,
                        help_text='Quantidade mínima no estoque (alertas futuros).',
                        max_digits=14,
                    ),
                ),
                (
                    'qrcode_imagem',
                    models.ImageField(
                        blank=True,
                        help_text='Imagem do QR Code do item (geração/leitura futura).',
                        null=True,
                        upload_to=estoque.upload_paths.item_qrcode_upload,
                        verbose_name='QR Code',
                    ),
                ),
                (
                    'categoria',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='itens',
                        to='estoque.categoriaitem',
                    ),
                ),
                (
                    'empresa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='itens_estoque',
                        to='empresas.empresa',
                    ),
                ),
                (
                    'fornecedor',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='itens_estoque',
                        to='fornecedores.fornecedor',
                    ),
                ),
                (
                    'unidade_medida',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='itens',
                        to='estoque.unidademedida',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Item',
                'verbose_name_plural': 'Itens',
                'ordering': ['descricao'],
            },
        ),
        migrations.CreateModel(
            name='ItemImagem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                (
                    'imagem',
                    models.ImageField(upload_to=estoque.upload_paths.item_imagem_upload),
                ),
                ('ordem', models.PositiveSmallIntegerField(default=0)),
                (
                    'item',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='imagens',
                        to='estoque.item',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Imagem do item',
                'verbose_name_plural': 'Imagens do item',
                'ordering': ['ordem', 'pk'],
            },
        ),
    ]
