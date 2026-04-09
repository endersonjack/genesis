# Generated manually for apontamento module access

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0002_usuarioempresa'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuarioempresa',
            name='apontador',
            field=models.BooleanField(
                default=False,
                help_text='Acesso ao módulo Apontamento (campo): registrar faltas e observações de local.',
            ),
        ),
    ]
