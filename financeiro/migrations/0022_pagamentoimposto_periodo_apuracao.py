from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0021_pagamentoimposto_data_pagamento_optional'),
    ]

    operations = [
        migrations.AddField(
            model_name='pagamentoimposto',
            name='periodo_apuracao',
            field=models.CharField(blank=True, max_length=60, verbose_name='Período de apuração'),
        ),
    ]
