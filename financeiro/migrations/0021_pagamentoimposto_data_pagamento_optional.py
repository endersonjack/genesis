from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0020_pagamentobancarioavulso'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pagamentoimposto',
            name='data_pagamento',
            field=models.DateField(blank=True, db_index=True, null=True, verbose_name='Data de pagamento'),
        ),
    ]
