from decimal import Decimal

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0005_alter_empresa_endereco'),
        ('financeiro', '0014_pagamento_pessoal_geral'),
    ]

    operations = [
        migrations.CreateModel(
            name='AutoridadeTributaria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('nome', models.CharField(max_length=200)),
                ('esfera', models.CharField(choices=[('federal', 'Federal'), ('estadual', 'Estadual'), ('municipal', 'Municipal')], db_index=True, max_length=12)),
                ('cnpj', models.CharField(blank=True, max_length=18)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='autoridades_tributarias', to='empresas.empresa')),
            ],
            options={
                'verbose_name': 'Autoridade tributária',
                'verbose_name_plural': 'Autoridades tributárias',
                'ordering': ['esfera', 'nome'],
                'constraints': [
                    models.UniqueConstraint(fields=('empresa', 'nome'), name='financeiro_autoridade_tributaria_unica_por_empresa_nome'),
                ],
            },
        ),
        migrations.CreateModel(
            name='PagamentoImposto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('data_emissao', models.DateField(db_index=True, default=django.utils.timezone.localdate, verbose_name='Data de emissão')),
                ('data_pagamento', models.DateField(db_index=True, default=django.utils.timezone.localdate, verbose_name='Data de pagamento')),
                ('autoridade', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pagamentos_impostos', to='financeiro.autoridadetributaria', verbose_name='Autoridade tributária')),
                ('caixa', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pagamentos_impostos', to='financeiro.caixa', verbose_name='Caixa')),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pagamentos_impostos', to='empresas.empresa')),
            ],
            options={
                'verbose_name': 'Pagamento de imposto',
                'verbose_name_plural': 'Pagamentos de impostos',
                'ordering': ['-data_emissao', '-pk'],
                'indexes': [
                    models.Index(fields=['empresa', 'data_emissao'], name='financeiro__empresa_f32e0d_idx'),
                    models.Index(fields=['empresa', 'autoridade', 'data_emissao'], name='financeiro__empresa_6b9a3a_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='PagamentoImpostoItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('descricao', models.CharField(max_length=500)),
                ('valor_total', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=16)),
                ('categoria', models.ForeignKey(help_text='Categoria de saída (pagamento de impostos).', on_delete=django.db.models.deletion.PROTECT, related_name='pagamentos_impostos_itens', to='financeiro.categoriafinanceira')),
                ('pagamento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='itens', to='financeiro.pagamentoimposto')),
            ],
            options={
                'verbose_name': 'Item de pagamento de imposto',
                'verbose_name_plural': 'Itens de pagamento de imposto',
                'ordering': ['pk'],
            },
        ),
    ]
