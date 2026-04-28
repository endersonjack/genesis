import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0005_alter_empresa_endereco'),
        ('financeiro', '0003_recebimentomedicao_nota_fiscal'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoriaFinanceira',
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
                        choices=[
                            ('entrada', 'Entrada (Recebimento)'),
                            ('saida', 'Saída (Pagamento)'),
                        ],
                        db_index=True,
                        max_length=10,
                    ),
                ),
                ('nome', models.CharField(max_length=200)),
                (
                    'ativo',
                    models.BooleanField(
                        default=True,
                        help_text='Inativas não aparecem em novos lançamentos (histórico preservado).',
                    ),
                ),
                (
                    'empresa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='categorias_financeiras',
                        to='empresas.empresa',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Categoria financeira',
                'verbose_name_plural': 'Categorias financeiras',
                'ordering': ['tipo', 'nome'],
            },
        ),
        migrations.AddConstraint(
            model_name='categoriafinanceira',
            constraint=models.UniqueConstraint(
                fields=('empresa', 'tipo', 'nome'),
                name='financeiro_categoria_financeira_unica_por_empresa_tipo_nome',
            ),
        ),
    ]

