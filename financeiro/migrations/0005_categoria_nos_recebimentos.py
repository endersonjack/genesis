import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0004_categoria_financeira'),
    ]

    operations = [
        migrations.AddField(
            model_name='recebimentoavulso',
            name='categoria',
            field=models.ForeignKey(
                blank=True,
                help_text='Categoria de entrada (recebimento).',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='recebimentos_avulsos',
                to='financeiro.categoriafinanceira',
            ),
        ),
        migrations.AddField(
            model_name='recebimentomedicao',
            name='categoria',
            field=models.ForeignKey(
                blank=True,
                help_text='Categoria de entrada (recebimento).',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='recebimentos_medicao',
                to='financeiro.categoriafinanceira',
            ),
        ),
    ]

