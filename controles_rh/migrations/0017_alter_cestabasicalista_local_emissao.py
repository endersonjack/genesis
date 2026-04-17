from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('controles_rh', '0016_alteracaofolhacontrole'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cestabasicalista',
            name='local_emissao',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Vazio = local padrão do sistema (PARNAMIRIM - RN).',
                max_length=120,
                verbose_name='Local (cidade/UF)',
            ),
        ),
    ]
