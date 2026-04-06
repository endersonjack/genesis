# Local da lista vazio passa a usar Preferências da empresa no PDF

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('controles_rh', '0009_cestabasicaitem_data_recebimento'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cestabasicalista',
            name='local_emissao',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Vazio = usa o local padrão em Preferências da empresa, depois o fallback do sistema.',
                max_length=120,
                verbose_name='Local (cidade/UF)',
            ),
        ),
    ]
