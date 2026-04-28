from django.db import migrations, models


def preencher_movimentacao_tipo(apps, schema_editor):
    CategoriaFinanceira = apps.get_model('financeiro', 'CategoriaFinanceira')
    RecebimentoAvulso = apps.get_model('financeiro', 'RecebimentoAvulso')
    RecebimentoMedicao = apps.get_model('financeiro', 'RecebimentoMedicao')
    PagamentoNotaFiscalItem = apps.get_model('financeiro', 'PagamentoNotaFiscalItem')

    categorias_com_recebimento_avulso = set(
        RecebimentoAvulso.objects.exclude(categoria_id__isnull=True).values_list(
            'categoria_id', flat=True
        )
    )
    categorias_com_recebimento_medicao = set(
        RecebimentoMedicao.objects.exclude(categoria_id__isnull=True).values_list(
            'categoria_id', flat=True
        )
    )
    categorias_com_pagamento_nf = set(
        PagamentoNotaFiscalItem.objects.exclude(categoria_id__isnull=True).values_list(
            'categoria_id', flat=True
        )
    )

    for categoria in CategoriaFinanceira.objects.all():
        if categoria.pk in categorias_com_recebimento_medicao:
            movimentacao_tipo = 'rec_medicao'
        elif categoria.pk in categorias_com_recebimento_avulso:
            movimentacao_tipo = 'rec_avulso'
        elif categoria.pk in categorias_com_pagamento_nf:
            movimentacao_tipo = 'pag_nf'
        elif categoria.tipo == 'entrada':
            movimentacao_tipo = 'rec_avulso'
        else:
            movimentacao_tipo = 'pag_nf'

        CategoriaFinanceira.objects.filter(pk=categoria.pk).update(
            movimentacao_tipo=movimentacao_tipo
        )


def desfazer_movimentacao_tipo(apps, schema_editor):
    CategoriaFinanceira = apps.get_model('financeiro', 'CategoriaFinanceira')
    CategoriaFinanceira.objects.update(movimentacao_tipo='rec_avulso')


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0007_rename_financeiro__empresa_16b4c2_idx_financeiro__empresa_776cfa_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='categoriafinanceira',
            name='movimentacao_tipo',
            field=models.CharField(
                choices=[
                    ('rec_avulso', 'Recebimento'),
                    ('rec_medicao', 'Recebimento por medição'),
                    ('pag_nf', 'Pagamento: Nota Fiscal'),
                    ('pag_impostos', 'Pagamento: Impostos'),
                    ('pag_pessoal', 'Pagamento: Pessoal'),
                    ('pag_bancario', 'Pagamento: Bancário'),
                    ('pag_alugueis', 'Pagamento: Aluguéis'),
                    ('pag_veiculos', 'Pagamento: Veículos'),
                    ('pag_avulso', 'Pagamento: Avulso'),
                    ('pag_avulso_mensal', 'Pagamento: Avulso Mensal'),
                ],
                db_index=True,
                default='rec_avulso',
                max_length=20,
                verbose_name='Tipo de movimentação',
            ),
            preserve_default=False,
        ),
        migrations.RunPython(preencher_movimentacao_tipo, desfazer_movimentacao_tipo),
        migrations.AlterModelOptions(
            name='categoriafinanceira',
            options={
                'verbose_name': 'Categoria financeira',
                'verbose_name_plural': 'Categorias financeiras',
                'ordering': ['movimentacao_tipo', 'nome'],
            },
        ),
        migrations.RemoveConstraint(
            model_name='categoriafinanceira',
            name='financeiro_categoria_financeira_unica_por_empresa_tipo_nome',
        ),
        migrations.AddConstraint(
            model_name='categoriafinanceira',
            constraint=models.UniqueConstraint(
                fields=('empresa', 'movimentacao_tipo', 'nome'),
                name='financeiro_categoria_financeira_unica_por_empresa_mov_tipo_nome',
            ),
        ),
    ]
