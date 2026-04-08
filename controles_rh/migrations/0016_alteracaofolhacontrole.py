import django.db.models.deletion
from django.db import migrations, models


def _criar_controle_para_linhas_existentes(apps, schema_editor):
    Competencia = apps.get_model('controles_rh', 'Competencia')
    AlteracaoFolhaControle = apps.get_model('controles_rh', 'AlteracaoFolhaControle')
    AlteracaoFolhaLinha = apps.get_model('controles_rh', 'AlteracaoFolhaLinha')
    com_linhas = (
        AlteracaoFolhaLinha.objects.values_list('competencia_id', flat=True)
        .distinct()
    )
    for cid in com_linhas:
        if not AlteracaoFolhaControle.objects.filter(competencia_id=cid).exists():
            AlteracaoFolhaControle.objects.create(competencia_id=cid)


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('controles_rh', '0015_alteracaofolhalinha'),
    ]

    operations = [
        migrations.CreateModel(
            name='AlteracaoFolhaControle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_geracao', models.DateTimeField(auto_now_add=True)),
                (
                    'competencia',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='alteracao_folha_controle',
                        to='controles_rh.competencia',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Alteração de folha (geração)',
                'verbose_name_plural': 'Alterações de folha (gerações)',
            },
        ),
        migrations.RunPython(_criar_controle_para_linhas_existentes, _noop),
    ]
