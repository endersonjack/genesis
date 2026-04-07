from django.db import migrations, models


def _backfill_viagens_dia(apps, schema_editor):
    ValeTransporteItem = apps.get_model('controles_rh', 'ValeTransporteItem')
    # Mantém compatibilidade: itens existentes passam a ter multiplicador 2 (ida e volta).
    ValeTransporteItem.objects.filter(viagens_dia__isnull=True).update(viagens_dia=2)


class Migration(migrations.Migration):
    dependencies = [
        ('controles_rh', '0012_valetransporteitem_unitario_dias'),
    ]

    operations = [
        migrations.AddField(
            model_name='valetransporteitem',
            name='viagens_dia',
            field=models.PositiveSmallIntegerField(
                default=2,
                help_text='Multiplicador do valor unitário (ex.: ida e volta = 2).',
                verbose_name='Viagens/dia',
            ),
        ),
        migrations.RunPython(_backfill_viagens_dia, migrations.RunPython.noop),
    ]

