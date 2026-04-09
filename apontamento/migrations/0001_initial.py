# Generated manually

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('empresas', '0001_initial'),
        ('local', '0001_initial'),
        ('rh', '0015_falta_funcionario_subtipo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ApontamentoFalta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('data', models.DateField()),
                ('motivo', models.CharField(max_length=500)),
                ('observacao', models.TextField(blank=True)),
                (
                    'empresa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='apontamentos_falta',
                        to='empresas.empresa',
                    ),
                ),
                (
                    'funcionario',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='apontamentos_falta',
                        to='rh.funcionario',
                    ),
                ),
                (
                    'registrado_por',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='apontamentos_falta_registrados',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Falta (apontamento)',
                'verbose_name_plural': 'Faltas (apontamento)',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.CreateModel(
            name='ApontamentoObservacaoLocal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('data', models.DateField()),
                ('texto', models.TextField()),
                (
                    'empresa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='apontamentos_observacao_local',
                        to='empresas.empresa',
                    ),
                ),
                (
                    'local',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='apontamentos_observacao',
                        to='local.local',
                    ),
                ),
                (
                    'registrado_por',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='apontamentos_observacao_registrados',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Observação de local (apontamento)',
                'verbose_name_plural': 'Observações de local (apontamento)',
                'ordering': ['-criado_em'],
            },
        ),
    ]
