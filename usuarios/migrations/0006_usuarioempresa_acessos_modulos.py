from django.db import migrations, models


def forwards(apps, schema_editor):
    UsuarioEmpresa = apps.get_model('usuarios', 'UsuarioEmpresa')

    # Segurança: normaliza qualquer NULL legado (se existir).
    UsuarioEmpresa.objects.filter(editar_empresas__isnull=True).update(editar_empresas=False)
    UsuarioEmpresa.objects.filter(rh__isnull=True).update(rh=False)
    UsuarioEmpresa.objects.filter(estoque__isnull=True).update(estoque=False)
    UsuarioEmpresa.objects.filter(financeiro__isnull=True).update(financeiro=False)
    UsuarioEmpresa.objects.filter(clientes__isnull=True).update(clientes=True)
    UsuarioEmpresa.objects.filter(fornecedores__isnull=True).update(fornecedores=True)
    UsuarioEmpresa.objects.filter(locais__isnull=True).update(locais=True)
    UsuarioEmpresa.objects.filter(obras__isnull=True).update(obras=True)
    UsuarioEmpresa.objects.filter(auditoria_total__isnull=True).update(auditoria_total=False)
    UsuarioEmpresa.objects.filter(auditoria_sua__isnull=True).update(auditoria_sua=True)

    # No PostgreSQL, o AddField costuma não deixar DEFAULT no banco.
    if schema_editor.connection.vendor == 'postgresql':
        with schema_editor.connection.cursor() as c:
            c.execute(
                'ALTER TABLE usuarios_usuarioempresa '
                'ALTER COLUMN editar_empresas SET DEFAULT FALSE'
            )
            c.execute(
                'ALTER TABLE usuarios_usuarioempresa '
                'ALTER COLUMN rh SET DEFAULT FALSE'
            )
            c.execute(
                'ALTER TABLE usuarios_usuarioempresa '
                'ALTER COLUMN estoque SET DEFAULT FALSE'
            )
            c.execute(
                'ALTER TABLE usuarios_usuarioempresa '
                'ALTER COLUMN financeiro SET DEFAULT FALSE'
            )
            c.execute(
                'ALTER TABLE usuarios_usuarioempresa '
                'ALTER COLUMN clientes SET DEFAULT TRUE'
            )
            c.execute(
                'ALTER TABLE usuarios_usuarioempresa '
                'ALTER COLUMN fornecedores SET DEFAULT TRUE'
            )
            c.execute(
                'ALTER TABLE usuarios_usuarioempresa '
                'ALTER COLUMN locais SET DEFAULT TRUE'
            )
            c.execute(
                'ALTER TABLE usuarios_usuarioempresa '
                'ALTER COLUMN obras SET DEFAULT TRUE'
            )
            c.execute(
                'ALTER TABLE usuarios_usuarioempresa '
                'ALTER COLUMN auditoria_total SET DEFAULT FALSE'
            )
            c.execute(
                'ALTER TABLE usuarios_usuarioempresa '
                'ALTER COLUMN auditoria_sua SET DEFAULT TRUE'
            )


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('usuarios', '0005_usuario_foto'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuarioempresa',
            name='editar_empresas',
            field=models.BooleanField(
                default=False,
                help_text='Permite editar as preferências da empresa (dados, logo e configurações).',
                verbose_name='Editar empresas (preferências)',
            ),
        ),
        migrations.AddField(
            model_name='usuarioempresa',
            name='rh',
            field=models.BooleanField(
                default=False,
                help_text='Libera acesso ao módulo de Recursos Humanos nesta empresa.',
                verbose_name='RH',
            ),
        ),
        migrations.AddField(
            model_name='usuarioempresa',
            name='estoque',
            field=models.BooleanField(
                default=False,
                help_text='Libera acesso ao módulo de Estoque nesta empresa.',
                verbose_name='Estoque',
            ),
        ),
        migrations.AddField(
            model_name='usuarioempresa',
            name='financeiro',
            field=models.BooleanField(
                default=False,
                help_text='Libera acesso ao módulo Financeiro nesta empresa.',
                verbose_name='Financeiro',
            ),
        ),
        migrations.AddField(
            model_name='usuarioempresa',
            name='clientes',
            field=models.BooleanField(
                default=True,
                help_text='Libera acesso ao cadastro de Clientes nesta empresa.',
                verbose_name='Clientes',
            ),
        ),
        migrations.AddField(
            model_name='usuarioempresa',
            name='fornecedores',
            field=models.BooleanField(
                default=True,
                help_text='Libera acesso ao cadastro de Fornecedores nesta empresa.',
                verbose_name='Fornecedores',
            ),
        ),
        migrations.AddField(
            model_name='usuarioempresa',
            name='locais',
            field=models.BooleanField(
                default=True,
                help_text='Libera acesso ao cadastro de Locais nesta empresa.',
                verbose_name='Locais',
            ),
        ),
        migrations.AddField(
            model_name='usuarioempresa',
            name='obras',
            field=models.BooleanField(
                default=True,
                help_text='Libera acesso ao cadastro de Obras nesta empresa.',
                verbose_name='Obras',
            ),
        ),
        migrations.AddField(
            model_name='usuarioempresa',
            name='auditoria_total',
            field=models.BooleanField(
                default=False,
                help_text='Permite visualizar a auditoria de todos os usuários na empresa.',
                verbose_name='Auditoria total',
            ),
        ),
        migrations.AddField(
            model_name='usuarioempresa',
            name='auditoria_sua',
            field=models.BooleanField(
                default=True,
                help_text='Permite visualizar a auditoria apenas das próprias ações na empresa.',
                verbose_name='Auditoria sua',
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]

