from decimal import Decimal

from django.db import migrations, models


def preencher_valor_liquido(apps, schema_editor):
    RecebimentoAvulso = apps.get_model('financeiro', 'RecebimentoAvulso')
    RecebimentoMedicao = apps.get_model('financeiro', 'RecebimentoMedicao')
    for model in (RecebimentoAvulso, RecebimentoMedicao):
        for recebimento in model.objects.all().only('pk', 'valor', 'impostos'):
            valor = recebimento.valor or Decimal('0')
            impostos = recebimento.impostos or Decimal('0')
            model.objects.filter(pk=recebimento.pk).update(valor_liquido=valor - impostos)


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0010_recebimentos_status_liquidacao'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recebimentoavulso',
            name='data_pagamento',
            field=models.DateField(
                'Data de liquidação',
                blank=True,
                db_index=True,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='recebimentomedicao',
            name='data_pagamento',
            field=models.DateField(
                'Data de liquidação',
                blank=True,
                db_index=True,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='recebimentoavulso',
            name='impostos',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=16),
        ),
        migrations.AddField(
            model_name='recebimentoavulso',
            name='valor_liquido',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=16),
        ),
        migrations.AddField(
            model_name='recebimentomedicao',
            name='impostos',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=16),
        ),
        migrations.AddField(
            model_name='recebimentomedicao',
            name='valor_liquido',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=16),
        ),
        migrations.RunPython(preencher_valor_liquido, migrations.RunPython.noop),
    ]
