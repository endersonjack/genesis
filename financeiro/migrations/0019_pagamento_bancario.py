# Generated manually because Django is unavailable in the current execution environment.

import decimal
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0018_rename_financeiro__empresa_16b4c2_idx_financeiro__empresa_776cfa_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PagamentoBancarioRecorrente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('dia_pagamento', models.PositiveSmallIntegerField(verbose_name='Dia do pagamento')),
                ('data_inicio', models.DateField(db_index=True, verbose_name='Data início')),
                ('qtd_parcelas', models.PositiveIntegerField(blank=True, null=True, verbose_name='Qtd parcelas')),
                ('data_fim', models.DateField(blank=True, db_index=True, null=True, verbose_name='Data fim')),
                ('valor_parcela', models.DecimalField(decimal_places=2, default=decimal.Decimal('0'), max_digits=16)),
                ('descricao', models.CharField(max_length=500)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
                ('caixa', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pagamentos_bancarios_recorrentes', to='financeiro.caixa', verbose_name='Caixa')),
                ('categoria', models.ForeignKey(help_text='Categoria de saída (pagamento bancário).', on_delete=django.db.models.deletion.PROTECT, related_name='pagamentos_bancarios_recorrentes', to='financeiro.categoriafinanceira')),
                ('conta_bancaria', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pagamentos_bancarios_recorrentes', to='financeiro.contabancaria', verbose_name='Banco')),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pagamentos_bancarios_recorrentes', to='empresas.empresa')),
            ],
            options={
                'verbose_name': 'Pagamento bancário recorrente',
                'verbose_name_plural': 'Pagamentos bancários recorrentes',
                'ordering': ['-data_inicio', '-pk'],
            },
        ),
        migrations.CreateModel(
            name='PagamentoBancarioParcela',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('numero_parcela', models.PositiveIntegerField(verbose_name='Nº parcela')),
                ('data_vencimento', models.DateField(db_index=True, verbose_name='Data do pagamento')),
                ('valor', models.DecimalField(decimal_places=2, default=decimal.Decimal('0'), max_digits=16)),
                ('status', models.CharField(choices=[('aberto', 'Em aberto'), ('pago', 'Pago'), ('cancelado', 'Cancelado')], db_index=True, default='aberto', max_length=12)),
                ('data_pagamento', models.DateField(blank=True, db_index=True, null=True, verbose_name='Data de pagamento')),
                ('observacao', models.TextField(blank=True)),
                ('conta_bancaria', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='pagamentos_bancarios_parcelas', to='financeiro.contabancaria', verbose_name='Pagamento realizado em')),
                ('recorrencia', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parcelas', to='financeiro.pagamentobancariorecorrente')),
            ],
            options={
                'verbose_name': 'Parcela de pagamento bancário',
                'verbose_name_plural': 'Parcelas de pagamentos bancários',
                'ordering': ['data_vencimento', 'numero_parcela', 'pk'],
            },
        ),
        migrations.AddIndex(
            model_name='pagamentobancariorecorrente',
            index=models.Index(fields=['empresa', 'data_inicio'], name='financeiro__empresa_355de6_idx'),
        ),
        migrations.AddIndex(
            model_name='pagamentobancariorecorrente',
            index=models.Index(fields=['empresa', 'ativo'], name='financeiro__empresa_be4ed6_idx'),
        ),
        migrations.AddIndex(
            model_name='pagamentobancarioparcela',
            index=models.Index(fields=['status', 'data_vencimento'], name='financeiro__status_1bd1d8_idx'),
        ),
        migrations.AddIndex(
            model_name='pagamentobancarioparcela',
            index=models.Index(fields=['data_pagamento'], name='financeiro__data_pa_d1f53b_idx'),
        ),
        migrations.AddConstraint(
            model_name='pagamentobancarioparcela',
            constraint=models.UniqueConstraint(fields=('recorrencia', 'numero_parcela'), name='financeiro_pag_bancario_parcela_unica'),
        ),
    ]
