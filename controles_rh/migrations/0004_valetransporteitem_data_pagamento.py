from django.db import migrations, models


def _ensure_data_pagamento(apps, schema_editor):
    conn = schema_editor.connection
    with conn.cursor() as cursor:
        if conn.vendor == 'postgresql':
            cursor.execute(
                'ALTER TABLE controles_rh_valetransporteitem ADD COLUMN IF NOT EXISTS '
                'data_pagamento date NULL'
            )
            return
        if conn.vendor == 'sqlite':
            cursor.execute('PRAGMA table_info("controles_rh_valetransporteitem")')
            names = {row[1] for row in cursor.fetchall()}
            if 'data_pagamento' not in names:
                cursor.execute(
                    'ALTER TABLE "controles_rh_valetransporteitem" '
                    'ADD COLUMN "data_pagamento" date NULL'
                )


def _noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('controles_rh', '0003_vt_status_valor_pago'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(_ensure_data_pagamento, _noop_reverse),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='valetransporteitem',
                    name='data_pagamento',
                    field=models.DateField(
                        blank=True,
                        null=True,
                        verbose_name='Data de pagamento',
                    ),
                ),
            ],
        ),
    ]
