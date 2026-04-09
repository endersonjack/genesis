# Corrige NULL em apontador e define DEFAULT no PostgreSQL (AddField remove o default do banco).

from django.db import migrations


def forwards(apps, schema_editor):
    UsuarioEmpresa = apps.get_model('usuarios', 'UsuarioEmpresa')
    UsuarioEmpresa.objects.filter(apontador__isnull=True).update(apontador=False)

    if schema_editor.connection.vendor == 'postgresql':
        with schema_editor.connection.cursor() as c:
            c.execute(
                'ALTER TABLE usuarios_usuarioempresa '
                'ALTER COLUMN apontador SET DEFAULT FALSE'
            )


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0003_usuarioempresa_apontador'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
