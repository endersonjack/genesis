from django.db import migrations, models


def _ensure_columns(apps, schema_editor):
    """Cria colunas só se ainda não existirem (evita erro quando o banco já foi alterado manualmente)."""
    conn = schema_editor.connection
    with conn.cursor() as cursor:
        if conn.vendor == 'postgresql':
            for sql in (
                'ALTER TABLE controles_rh_competencia ADD COLUMN IF NOT EXISTS '
                'vt_calculo_automatico boolean NOT NULL DEFAULT true',
                'ALTER TABLE controles_rh_competencia ADD COLUMN IF NOT EXISTS '
                'vt_status_manual varchar(20) NULL',
                'ALTER TABLE controles_rh_valetransportetabela ADD COLUMN IF NOT EXISTS '
                'vt_calculo_automatico boolean NOT NULL DEFAULT true',
                'ALTER TABLE controles_rh_valetransportetabela ADD COLUMN IF NOT EXISTS '
                'vt_status_manual varchar(20) NULL',
                'ALTER TABLE controles_rh_valetransporteitem ADD COLUMN IF NOT EXISTS '
                'valor_pago numeric(10,2) NOT NULL DEFAULT 0',
            ):
                cursor.execute(sql)
            return

        if conn.vendor == 'sqlite':
            def cols(table):
                cursor.execute(f'PRAGMA table_info("{table}")')
                return {row[1] for row in cursor.fetchall()}

            specs = [
                (
                    'controles_rh_competencia',
                    [
                        ('vt_calculo_automatico', 'bool NOT NULL DEFAULT 1'),
                        ('vt_status_manual', 'varchar(20) NULL'),
                    ],
                ),
                (
                    'controles_rh_valetransportetabela',
                    [
                        ('vt_calculo_automatico', 'bool NOT NULL DEFAULT 1'),
                        ('vt_status_manual', 'varchar(20) NULL'),
                    ],
                ),
                (
                    'controles_rh_valetransporteitem',
                    [
                        ('valor_pago', 'decimal(10,2) NOT NULL DEFAULT 0'),
                    ],
                ),
            ]
            for table, additions in specs:
                existing = cols(table)
                for name, ddl in additions:
                    if name not in existing:
                        cursor.execute(
                            f'ALTER TABLE "{table}" ADD COLUMN "{name}" {ddl}'
                        )
            return

    # Outros backends: deixa o estado do Django alinhado; se faltar coluna, makemigrations/manual.
    pass


def _noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('controles_rh', '0002_alter_competencia_unique_together'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(_ensure_columns, _noop_reverse),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='competencia',
                    name='vt_calculo_automatico',
                    field=models.BooleanField(
                        default=True,
                        help_text='Quando ativo, o status de pagamento do VT é calculado pelas tabelas e itens.',
                        verbose_name='Status VT automático',
                    ),
                ),
                migrations.AddField(
                    model_name='competencia',
                    name='vt_status_manual',
                    field=models.CharField(
                        blank=True,
                        choices=[
                            ('em_pagamento', 'Em pagamento'),
                            ('pago_completo', 'Pago completo'),
                        ],
                        help_text='Usado apenas quando o status automático está desligado.',
                        max_length=20,
                        null=True,
                        verbose_name='Status VT manual',
                    ),
                ),
                migrations.AddField(
                    model_name='valetransportetabela',
                    name='vt_calculo_automatico',
                    field=models.BooleanField(
                        default=True,
                        help_text='Quando ativo, o status é calculado pelos itens (valores a pagar x pagos).',
                        verbose_name='Status pagamento automático',
                    ),
                ),
                migrations.AddField(
                    model_name='valetransportetabela',
                    name='vt_status_manual',
                    field=models.CharField(
                        blank=True,
                        choices=[
                            ('em_pagamento', 'Em pagamento'),
                            ('pago_completo', 'Pago completo'),
                        ],
                        help_text='Usado apenas quando o cálculo automático está desligado.',
                        max_length=20,
                        null=True,
                        verbose_name='Status pagamento manual',
                    ),
                ),
                migrations.AddField(
                    model_name='valetransporteitem',
                    name='valor_pago',
                    field=models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=10,
                        verbose_name='Valor pago',
                    ),
                ),
            ],
        ),
    ]
