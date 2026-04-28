from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0008_categoria_financeira_movimentacao_tipo'),
    ]

    operations = [
        migrations.AddField(
            model_name='boletopagamento',
            name='acrescimos',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                max_digits=16,
            ),
        ),
        migrations.AddField(
            model_name='boletopagamento',
            name='descontos',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                max_digits=16,
            ),
        ),
    ]
