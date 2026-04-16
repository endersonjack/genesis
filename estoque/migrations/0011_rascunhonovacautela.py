import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('empresas', '0004_empresa_logo'),
        ('estoque', '0009_cautela_ferramentas'),
    ]

    operations = [
        migrations.CreateModel(
            name='RascunhoNovaCautela',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                (
                    'dados',
                    models.JSONField(
                        default=dict,
                        help_text='JSON com chaves form (campos do formulário) e items (ferramentas).',
                    ),
                ),
                (
                    'empresa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='rascunhos_nova_cautela',
                        to='empresas.empresa',
                    ),
                ),
                (
                    'usuario',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='rascunhos_nova_cautela_estoque',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Rascunho de nova cautela',
                'verbose_name_plural': 'Rascunhos de nova cautela',
            },
        ),
        migrations.AddConstraint(
            model_name='rascunhonovacautela',
            constraint=models.UniqueConstraint(
                fields=('empresa', 'usuario'),
                name='uniq_rascunho_nova_cautela_empresa_usuario',
            ),
        ),
    ]
