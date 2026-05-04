import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0013_pagamento_pessoal'),
        ('rh', '0016_funcionario_local_trabalho'),
    ]

    operations = [
        migrations.AddField(
            model_name='pagamentopessoal',
            name='tipo_destino',
            field=models.CharField(
                choices=[('funcionario', 'Funcionário'), ('geral', 'Geral')],
                db_index=True,
                default='funcionario',
                max_length=12,
            ),
        ),
        migrations.AlterField(
            model_name='pagamentopessoal',
            name='funcionario',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='pagamentos_pessoal',
                to='rh.funcionario',
                verbose_name='Funcionário',
            ),
        ),
    ]
