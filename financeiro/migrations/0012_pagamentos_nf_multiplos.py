import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0011_recebimentos_impostos_liquidacao'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pagamentonotafiscalpagamento',
            name='pagamento_nf',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='pagamentos',
                to='financeiro.pagamentonotafiscal',
            ),
        ),
    ]
