from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('controles_rh', '0013_valetransporteitem_viagens_dia'),
    ]

    operations = [
        migrations.AlterField(
            model_name='valetransporteitem',
            name='dias',
            field=models.PositiveSmallIntegerField(
                default=20,
                help_text='Quantidade de dias usada para calcular o total.',
                verbose_name='Dias',
            ),
        ),
    ]

