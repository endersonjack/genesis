from django.db import migrations, models


def forwards(apps, schema_editor):
    UsuarioEmpresa = apps.get_model('usuarios', 'UsuarioEmpresa')
    UsuarioEmpresa.objects.filter(
        obras_empresas_acessiveis__isnull=True
    ).update(obras_empresas_acessiveis=False)
    UsuarioEmpresa.objects.filter(obras=False).update(
        obras_empresas_acessiveis=False
    )

    if schema_editor.connection.vendor == 'postgresql':
        with schema_editor.connection.cursor() as c:
            c.execute(
                'ALTER TABLE usuarios_usuarioempresa '
                'ALTER COLUMN obras_empresas_acessiveis SET DEFAULT FALSE'
            )


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('usuarios', '0008_usuarioempresa_estoque_funcionarios_empresas_acessiveis'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuarioempresa',
            name='obras_empresas_acessiveis',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'No módulo Obras desta empresa, permite acessar obras de outras '
                    'empresas ativas às quais o usuário também tem acesso.'
                ),
                verbose_name='Obras: empresas acessíveis',
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]
