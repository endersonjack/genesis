from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0002_recebimentos_caixa'),
    ]

    operations = [
        migrations.AddField(
            model_name='recebimentomedicao',
            name='nota_fiscal_numero',
            field=models.CharField(
                blank=True,
                help_text='Opcional. Número da NF-e ou documento fiscal, quando houver.',
                max_length=60,
                verbose_name='Nº nota fiscal',
            ),
        ),
    ]
