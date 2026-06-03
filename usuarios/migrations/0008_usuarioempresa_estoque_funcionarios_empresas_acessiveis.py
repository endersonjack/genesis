from django.db import migrations, models


def forwards(apps, schema_editor):
    UsuarioEmpresa = apps.get_model('usuarios', 'UsuarioEmpresa')
    UsuarioEmpresa.objects.filter(
        estoque_funcionarios_empresas_acessiveis__isnull=True
    ).update(estoque_funcionarios_empresas_acessiveis=False)
    UsuarioEmpresa.objects.filter(estoque=False).update(
        estoque_funcionarios_empresas_acessiveis=False
    )

    if schema_editor.connection.vendor == 'postgresql':
        with schema_editor.connection.cursor() as c:
            c.execute(
                'ALTER TABLE usuarios_usuarioempresa '
                'ALTER COLUMN estoque_funcionarios_empresas_acessiveis SET DEFAULT FALSE'
            )


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('usuarios', '0007_alter_usuarioempresa_apontador'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuarioempresa',
            name='estoque_funcionarios_empresas_acessiveis',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'No Estoque desta empresa, permite selecionar funcionários de outras '
                    'empresas ativas às quais o usuário também tem acesso.'
                ),
                verbose_name='Estoque: funcionários de empresas acessíveis',
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]
