from django.db import migrations, models


def _ensure_valor_base(apps, schema_editor):
    conn = schema_editor.connection
    with conn.cursor() as cursor:
        if conn.vendor == 'postgresql':
            cursor.execute(
                'ALTER TABLE controles_rh_valetransporteitem ADD COLUMN IF NOT EXISTS '
                'valor_base numeric(10,2) NOT NULL DEFAULT 0'
            )
            cursor.execute(
                'UPDATE controles_rh_valetransporteitem SET valor_base = COALESCE(valor_pagar, 0) '
                'WHERE valor_base IS NULL'
            )
            return
        if conn.vendor == 'sqlite':
            cursor.execute('PRAGMA table_info("controles_rh_valetransporteitem")')
            names = {row[1] for row in cursor.fetchall()}
            if 'valor_base' not in names:
                cursor.execute(
                    'ALTER TABLE "controles_rh_valetransporteitem" '
                    'ADD COLUMN "valor_base" decimal(10,2) NOT NULL DEFAULT 0'
                )
            cursor.execute(
                'UPDATE controles_rh_valetransporteitem SET valor_base = COALESCE(valor_pagar, 0) '
                'WHERE valor_base IS NULL'
            )


def _noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('controles_rh', '0004_valetransporteitem_data_pagamento'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(_ensure_valor_base, _noop_reverse),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='valetransporteitem',
                    name='valor_base',
                    field=models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text='Valor de referência (espelha o valor a pagar na prática).',
                        max_digits=10,
                        verbose_name='Valor base',
                    ),
                ),
            ],
        ),
    ]
