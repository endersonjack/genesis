from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0015_listacompraestoque_listacompraestoqueitem_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='listacompraestoque',
            name='nome',
            field=models.CharField(
                blank=True,
                help_text='Identificação opcional (ex.: compras da semana, obra X).',
                max_length=200,
                verbose_name='Nome da lista',
            ),
        ),
    ]
