from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0023_pagamentoimposto_data_vencimento'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pagamentopessoal',
            name='data_pagamento',
            field=models.DateField(
                blank=True,
                db_index=True,
                null=True,
                verbose_name='Data de pagamento',
            ),
        ),
    ]
