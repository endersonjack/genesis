from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0006_usuarioempresa_acessos_modulos'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usuarioempresa',
            name='apontador',
            field=models.BooleanField(
                default=False,
                help_text='Libera o módulo Apontamento (campo) nesta empresa: faltas e observações de local.',
                verbose_name='Apontador',
            ),
        ),
    ]
