from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models


def copiar_movimento_para_recebimentos(apps, schema_editor):
    RecebimentoAvulso = apps.get_model('financeiro', 'RecebimentoAvulso')
    RecebimentoMedicao = apps.get_model('financeiro', 'RecebimentoMedicao')

    for recebimento in RecebimentoAvulso.objects.select_related('movimento'):
        mov = recebimento.movimento
        if not mov:
            continue
        RecebimentoAvulso.objects.filter(pk=recebimento.pk).update(
            empresa_id=mov.empresa_id,
            caixa_id=mov.caixa_id,
            status='pago',
            data=mov.data,
            data_pagamento=mov.data,
            valor=mov.valor,
            descricao=mov.descricao,
            observacao=mov.observacao,
        )

    for recebimento in RecebimentoMedicao.objects.select_related('movimento'):
        mov = recebimento.movimento
        if not mov:
            continue
        RecebimentoMedicao.objects.filter(pk=recebimento.pk).update(
            empresa_id=mov.empresa_id,
            caixa_id=mov.caixa_id,
            status='pago',
            data=mov.data,
            data_pagamento=mov.data,
            valor=mov.valor,
            descricao=mov.descricao,
            observacao=mov.observacao,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0009_boleto_pagamento_ajustes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recebimentoavulso',
            name='movimento',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='recebimento_avulso',
                to='financeiro.movimentocaixa',
            ),
        ),
        migrations.AlterField(
            model_name='recebimentomedicao',
            name='movimento',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='recebimento_medicao',
                to='financeiro.movimentocaixa',
            ),
        ),
        migrations.AddField(
            model_name='recebimentoavulso',
            name='empresa',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='recebimentos_avulsos',
                to='empresas.empresa',
            ),
        ),
        migrations.AddField(
            model_name='recebimentoavulso',
            name='caixa',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='recebimentos_avulsos',
                to='financeiro.caixa',
            ),
        ),
        migrations.AddField(
            model_name='recebimentoavulso',
            name='status',
            field=models.CharField(
                choices=[('aberto', 'Em aberto'), ('pago', 'Pago')],
                db_index=True,
                default='aberto',
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name='recebimentoavulso',
            name='data',
            field=models.DateField(blank=True, db_index=True, null=True, verbose_name='Data'),
        ),
        migrations.AddField(
            model_name='recebimentoavulso',
            name='data_pagamento',
            field=models.DateField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='recebimentoavulso',
            name='valor',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=16),
        ),
        migrations.AddField(
            model_name='recebimentoavulso',
            name='descricao',
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name='recebimentoavulso',
            name='observacao',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='recebimentomedicao',
            name='empresa',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='recebimentos_medicao',
                to='empresas.empresa',
            ),
        ),
        migrations.AddField(
            model_name='recebimentomedicao',
            name='caixa',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='recebimentos_medicao',
                to='financeiro.caixa',
            ),
        ),
        migrations.AddField(
            model_name='recebimentomedicao',
            name='status',
            field=models.CharField(
                choices=[('aberto', 'Em aberto'), ('pago', 'Pago')],
                db_index=True,
                default='aberto',
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name='recebimentomedicao',
            name='data',
            field=models.DateField(blank=True, db_index=True, null=True, verbose_name='Data'),
        ),
        migrations.AddField(
            model_name='recebimentomedicao',
            name='data_pagamento',
            field=models.DateField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='recebimentomedicao',
            name='valor',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=16),
        ),
        migrations.AddField(
            model_name='recebimentomedicao',
            name='descricao',
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name='recebimentomedicao',
            name='observacao',
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(copiar_movimento_para_recebimentos, migrations.RunPython.noop),
    ]
