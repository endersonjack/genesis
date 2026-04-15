import django.db.models.deletion
from django.db import migrations, models

import estoque.upload_paths


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0004_empresa_logo'),
        ('fornecedores', '0001_initial'),
        ('estoque', '0007_requisicao_estoque_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='Ferramenta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('descricao', models.CharField(max_length=500)),
                ('marca', models.CharField(blank=True, max_length=120)),
                ('cor', models.CharField(blank=True, max_length=64)),
                ('tamanho', models.CharField(blank=True, max_length=64)),
                (
                    'codigo_numeracao',
                    models.CharField(
                        blank=True,
                        help_text='Identificador interno ou de patrimônio (opcional).',
                        max_length=64,
                        verbose_name='Código / numeração',
                    ),
                ),
                ('preco', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                (
                    'ativo',
                    models.BooleanField(
                        default=True,
                        help_text='Ferramentas inativas não aparecem nas buscas principais.',
                    ),
                ),
                (
                    'qrcode_imagem',
                    models.ImageField(
                        blank=True,
                        help_text='Imagem do QR Code gerada ao salvar (leitor 2D nas telas de estoque).',
                        null=True,
                        upload_to=estoque.upload_paths.ferramenta_qrcode_upload,
                        verbose_name='QR Code',
                    ),
                ),
                ('observacoes', models.TextField(blank=True, verbose_name='Obs.')),
                (
                    'categoria',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='ferramentas',
                        to='estoque.categoriaferramenta',
                    ),
                ),
                (
                    'empresa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='ferramentas',
                        to='empresas.empresa',
                    ),
                ),
                (
                    'fornecedor',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='ferramentas_estoque',
                        to='fornecedores.fornecedor',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Ferramenta',
                'verbose_name_plural': 'Ferramentas',
                'ordering': ['descricao'],
            },
        ),
        migrations.CreateModel(
            name='FerramentaImagem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('imagem', models.ImageField(upload_to=estoque.upload_paths.ferramenta_imagem_upload)),
                ('ordem', models.PositiveSmallIntegerField(default=0)),
                (
                    'ferramenta',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='imagens',
                        to='estoque.ferramenta',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Imagem da ferramenta',
                'verbose_name_plural': 'Imagens da ferramenta',
                'ordering': ['ordem', 'pk'],
            },
        ),
    ]
