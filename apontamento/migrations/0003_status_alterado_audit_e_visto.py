import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def forwards_finalizado_para_visto(apps, schema_editor):
    ApontamentoFalta = apps.get_model('apontamento', 'ApontamentoFalta')
    ApontamentoObservacaoLocal = apps.get_model(
        'apontamento', 'ApontamentoObservacaoLocal'
    )
    for Model in (ApontamentoFalta, ApontamentoObservacaoLocal):
        Model.objects.filter(status='finalizado').update(status='visto')


class Migration(migrations.Migration):

    dependencies = [
        ('apontamento', '0002_apontamentofalta_status_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='apontamentofalta',
            name='status_alterado_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='apontamentos_falta_status_alterados',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='apontamentofalta',
            name='status_alterado_em',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='apontamentoobservacaolocal',
            name='status_alterado_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='apontamentos_observacao_status_alterados',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='apontamentoobservacaolocal',
            name='status_alterado_em',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(forwards_finalizado_para_visto, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='apontamentofalta',
            name='status',
            field=models.CharField(
                choices=[
                    ('pendente', 'Pendente'),
                    ('visto', 'Visto'),
                    ('arquivado', 'Arquivado'),
                ],
                db_index=True,
                default='pendente',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='apontamentoobservacaolocal',
            name='status',
            field=models.CharField(
                choices=[
                    ('pendente', 'Pendente'),
                    ('visto', 'Visto'),
                    ('arquivado', 'Arquivado'),
                ],
                db_index=True,
                default='pendente',
                max_length=20,
            ),
        ),
    ]
