from decimal import Decimal

from django.db import migrations, models


def _backfill_unitario_dias(apps, schema_editor):
    ValeTransporteItem = apps.get_model('controles_rh', 'ValeTransporteItem')
    qs = ValeTransporteItem.objects.all().only('id', 'valor_pagar', 'valor_unitario', 'dias')

    for item in qs.iterator():
        vu = getattr(item, 'valor_unitario', None)
        dias = getattr(item, 'dias', None)
        vp = getattr(item, 'valor_pagar', None)

        vu = vu if vu is not None else Decimal('0')
        dias = dias if dias is not None else 0
        vp = vp if vp is not None else Decimal('0')

        # Se já tiver sido preenchido manualmente, não mexe.
        if (vu and vu > 0) or (dias and dias > 0 and vu and vu > 0):
            continue

        # Preserva o total antigo: unitário = total, dias = 1
        if vp and vp > 0:
            item.valor_unitario = vp
            item.dias = 1
        else:
            item.valor_unitario = Decimal('0')
            item.dias = 1

        item.save(update_fields=['valor_unitario', 'dias'])


class Migration(migrations.Migration):
    dependencies = [
        ('controles_rh', '0011_cestabasicalista_recibo_altura_linha'),
    ]

    operations = [
        migrations.AddField(
            model_name='valetransporteitem',
            name='valor_unitario',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Valor unitário do vale transporte (ex.: por dia).',
                max_digits=10,
                verbose_name='Valor unitário',
            ),
        ),
        migrations.AddField(
            model_name='valetransporteitem',
            name='dias',
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text='Quantidade de dias usada para calcular o total.',
                verbose_name='Dias',
            ),
        ),
        migrations.AlterField(
            model_name='valetransporteitem',
            name='valor_pagar',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=10,
                verbose_name='Valor Total de VT',
            ),
        ),
        migrations.RunPython(_backfill_unitario_dias, migrations.RunPython.noop),
    ]

