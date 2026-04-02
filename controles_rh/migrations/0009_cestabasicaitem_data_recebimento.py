from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('controles_rh', '0008_cesta_basica_recebido_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='cestabasicaitem',
            name='data_recebimento',
            field=models.DateField(
                blank=True,
                null=True,
                verbose_name='Data de recebimento',
            ),
        ),
    ]
