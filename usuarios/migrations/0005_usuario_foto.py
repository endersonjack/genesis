from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0004_usuarioempresa_apontador_db_default'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='foto',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='usuarios/fotos/',
                verbose_name='Foto do perfil',
            ),
        ),
    ]
