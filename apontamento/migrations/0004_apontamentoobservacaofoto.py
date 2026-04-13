import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apontamento', '0003_status_alterado_audit_e_visto'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApontamentoObservacaoFoto',
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
                    'imagem',
                    models.ImageField(upload_to='apontamento/anotacoes/'),
                ),
                (
                    'observacao',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='fotos',
                        to='apontamento.apontamentoobservacaolocal',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Foto da anotação (apontamento)',
                'verbose_name_plural': 'Fotos das anotações (apontamento)',
                'ordering': ['id'],
            },
        ),
    ]
