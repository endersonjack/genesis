# Pagamento bancário avulso (dependente de 0019_pagamento_bancario)

import decimal
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0019_pagamento_bancario'),
    ]

    operations = [
        migrations.CreateModel(
            name='PagamentoBancarioAvulso',
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
                ('descricao', models.CharField(blank=True, max_length=500, verbose_name='Descrição')),
                ('data_pagamento', models.DateField(db_index=True, verbose_name='Data de pagamento')),
                (
                    'valor',
                    models.DecimalField(
                        decimal_places=2,
                        default=decimal.Decimal('0'),
                        max_digits=16,
                    ),
                ),
                ('observacao', models.TextField(blank=True, verbose_name='Observação')),
                (
                    'caixa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='pagamentos_bancarios_avulsos',
                        to='financeiro.caixa',
                        verbose_name='Caixa',
                    ),
                ),
                (
                    'categoria',
                    models.ForeignKey(
                        help_text='Categoria de saída (pagamento bancário).',
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='pagamentos_bancarios_avulsos',
                        to='financeiro.categoriafinanceira',
                    ),
                ),
                (
                    'conta_bancaria',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='pagamentos_bancarios_avulsos',
                        to='financeiro.contabancaria',
                        verbose_name='Banco',
                    ),
                ),
                (
                    'empresa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='pagamentos_bancarios_avulsos',
                        to='empresas.empresa',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Pagamento bancário avulso',
                'verbose_name_plural': 'Pagamentos bancários avulsos',
                'ordering': ('-data_pagamento', '-pk'),
            },
        ),
        migrations.AddIndex(
            model_name='pagamentobancarioavulso',
            index=models.Index(fields=('empresa', 'data_pagamento'), name='fin_pagbacav_emp_data_idx'),
        ),
    ]
