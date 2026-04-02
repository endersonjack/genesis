import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('controles_rh', '0006_cesta_basica'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cestabasicalista',
            options={
                'ordering': ['data_criacao', 'id'],
                'verbose_name': 'Lista de Cesta Básica',
                'verbose_name_plural': 'Listas de Cesta Básica',
            },
        ),
        migrations.AlterField(
            model_name='cestabasicalista',
            name='competencia',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='cestas_basicas',
                to='controles_rh.competencia',
            ),
        ),
    ]
