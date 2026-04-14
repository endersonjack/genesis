from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('estoque', '0005_item_ativo_quantidade_estoque'),
        ('rh', '0001_initial'),
        ('local', '0001_initial'),
        ('obras', '0001_initial'),
        ('usuarios', '0005_usuario_foto'),
    ]

    operations = [
        migrations.CreateModel(
            name='RequisicaoEstoque',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                (
                    'empresa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='requisicoes_estoque',
                        to='empresas.empresa',
                    ),
                ),
                (
                    'solicitante',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='requisicoes_estoque_solicitadas',
                        to='rh.funcionario',
                    ),
                ),
                (
                    'local',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='requisicoes_estoque',
                        to='local.local',
                    ),
                ),
                (
                    'obra',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='requisicoes_estoque',
                        to='obras.obra',
                    ),
                ),
                (
                    'almoxarife',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='requisicoes_estoque_almoxarife',
                        to='usuarios.usuario',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Requisição de estoque',
                'verbose_name_plural': 'Requisições de estoque',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.CreateModel(
            name='RequisicaoEstoqueItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantidade', models.DecimalField(decimal_places=4, default=0, max_digits=14)),
                (
                    'item',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='requisicoes_itens',
                        to='estoque.item',
                    ),
                ),
                (
                    'requisicao',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='itens',
                        to='estoque.requisicaoestoque',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Item requisitado',
                'verbose_name_plural': 'Itens requisitados',
                'ordering': ['pk'],
            },
        ),
        migrations.AddIndex(
            model_name='requisicaoestoque',
            index=models.Index(fields=['empresa', 'criado_em'], name='estoque_req_empresa_criado'),
        ),
        migrations.AddConstraint(
            model_name='requisicaoestoqueitem',
            constraint=models.UniqueConstraint(fields=('requisicao', 'item'), name='unique_item_por_requisicao'),
        ),
    ]

