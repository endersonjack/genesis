# Após o merge: copia anexos do campo legado `foto` para ApontamentoObservacaoFoto e remove o campo.

import django.db.models.deletion
from django.db import migrations, models


def forwards_copiar_foto_legacy(apps, schema_editor):
    Obs = apps.get_model('apontamento', 'ApontamentoObservacaoLocal')
    Foto = apps.get_model('apontamento', 'ApontamentoObservacaoFoto')
    for obs in Obs.objects.all():
        raw = getattr(obs, 'foto', None)
        if not raw:
            continue
        Foto.objects.create(observacao_id=obs.pk, imagem=raw)


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('apontamento', '0005_merge_apontamento_foto_branches'),
    ]

    operations = [
        migrations.RunPython(forwards_copiar_foto_legacy, backwards_noop),
        migrations.RemoveField(
            model_name='apontamentoobservacaolocal',
            name='foto',
        ),
    ]
