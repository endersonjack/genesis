from decimal import Decimal

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0005_alter_empresa_endereco'),
        ('financeiro', '0012_pagamentos_nf_multiplos'),
        ('rh', '0016_funcionario_local_trabalho'),
    ]

    operations = [
        migrations.CreateModel(
            name='PagamentoPessoal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('data_emissao', models.DateField(db_index=True, default=django.utils.timezone.localdate, verbose_name='Data de emissão')),
                ('descricao', models.CharField(blank=True, max_length=500, verbose_name='Descrição')),
                ('data_pagamento', models.DateField(db_index=True, default=django.utils.timezone.localdate, verbose_name='Data de pagamento')),
                ('caixa', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pagamentos_pessoal', to='financeiro.caixa', verbose_name='Caixa')),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pagamentos_pessoal', to='empresas.empresa')),
                ('funcionario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pagamentos_pessoal', to='rh.funcionario', verbose_name='Funcionário')),
            ],
            options={
                'verbose_name': 'Pagamento pessoal',
                'verbose_name_plural': 'Pagamentos pessoais',
                'ordering': ['-data_emissao', '-pk'],
                'indexes': [
                    models.Index(fields=['empresa', 'data_emissao'], name='financeiro__empresa_893d11_idx'),
                    models.Index(fields=['empresa', 'funcionario', 'data_emissao'], name='financeiro__empresa_9c6000_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='PagamentoPessoalItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('descricao', models.CharField(max_length=500)),
                ('valor_total', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=16)),
                ('categoria', models.ForeignKey(help_text='Categoria de saída (pagamento pessoal).', on_delete=django.db.models.deletion.PROTECT, related_name='pagamentos_pessoal_itens', to='financeiro.categoriafinanceira')),
                ('pagamento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='itens', to='financeiro.pagamentopessoal')),
            ],
            options={
                'verbose_name': 'Item de pagamento pessoal',
                'verbose_name_plural': 'Itens de pagamento pessoal',
                'ordering': ['pk'],
            },
        ),
    ]
