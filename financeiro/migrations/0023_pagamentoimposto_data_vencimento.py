from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0022_pagamentoimposto_periodo_apuracao'),
    ]

    operations = [
        migrations.AddField(
            model_name='pagamentoimposto',
            name='data_vencimento',
            field=models.DateField(blank=True, db_index=True, null=True, verbose_name='Data de vencimento'),
        ),
    ]
