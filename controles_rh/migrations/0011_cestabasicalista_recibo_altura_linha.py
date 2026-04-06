# Altura de linha do PDF (recibo) ajustável

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('controles_rh', '0010_cestabasicalista_local_emissao_default'),
    ]

    operations = [
        migrations.AddField(
            model_name='cestabasicalista',
            name='recibo_altura_linha_pct',
            field=models.PositiveSmallIntegerField(
                default=100,
                help_text='Percentual: 100 = padrão. Aumente para linhas mais altas na tabela.',
                validators=[
                    django.core.validators.MinValueValidator(70),
                    django.core.validators.MaxValueValidator(180),
                ],
                verbose_name='Altura da linha no PDF (recibo/relatório)',
            ),
        ),
    ]
