import django.db.models.deletion
from django.db import migrations, models


def criar_caixa_geral_por_empresa(apps, schema_editor):
    Empresa = apps.get_model('empresas', 'Empresa')
    Caixa = apps.get_model('financeiro', 'Caixa')
    for emp in Empresa.objects.all():
        Caixa.objects.get_or_create(
            empresa_id=emp.pk,
            tipo='geral',
            defaults={'nome': 'Caixa geral', 'ativo': True},
        )


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('empresas', '0005_alter_empresa_endereco'),
        ('obras', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Caixa',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                (
                    'tipo',
                    models.CharField(
                        choices=[
                            ('geral', 'Caixa geral'),
                            ('obra', 'Subcaixa de obra'),
                            ('personalizada', 'Subcaixa personalizada'),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                (
                    'nome',
                    models.CharField(
                        help_text='Para o caixa geral use «Caixa geral». Subcaixa de obra costuma repetir o nome da obra.',
                        max_length=200,
                    ),
                ),
                (
                    'ativo',
                    models.BooleanField(
                        default=True,
                        help_text='Inativas não aparecem em lançamentos novos (histórico preservado).',
                    ),
                ),
                (
                    'empresa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='caixas_financeiro',
                        to='empresas.empresa',
                    ),
                ),
                (
                    'obra',
                    models.ForeignKey(
                        blank=True,
                        help_text='Obrigatório para subcaixa de obra; vazio para caixa geral ou personalizada.',
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='caixas_financeiro',
                        to='obras.obra',
                        verbose_name='Obra',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Caixa',
                'verbose_name_plural': 'Caixas',
                'ordering': ['tipo', 'nome'],
            },
        ),
        migrations.CreateModel(
            name='MovimentoCaixa',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                (
                    'natureza',
                    models.CharField(
                        choices=[('entrada', 'Entrada'), ('saida', 'Saída')],
                        db_index=True,
                        max_length=10,
                    ),
                ),
                (
                    'categoria_origem',
                    models.CharField(
                        choices=[
                            ('rec_avulso', 'Recebimento avulso'),
                            ('rec_contrato', 'Recebimento (contrato)'),
                            ('pag_avulso', 'Pagamento avulso'),
                            ('pag_vista', 'Pagamento à vista'),
                            ('pag_boleto', 'Pagamento de boleto'),
                            ('transf_caixa', 'Transferência entre caixas'),
                            ('outro', 'Outro'),
                        ],
                        db_index=True,
                        default='outro',
                        help_text='Classificação do lançamento (recibo, contrato, boleto, etc.).',
                        max_length=20,
                        verbose_name='Origem',
                    ),
                ),
                (
                    'meio_pagamento',
                    models.CharField(
                        blank=True,
                        choices=[
                            ('pix', 'PIX'),
                            ('dinheiro', 'Dinheiro'),
                            ('boleto', 'Boleto'),
                            ('transferencia', 'Transferência bancária'),
                            ('cartao', 'Cartão'),
                            ('outro', 'Outro'),
                        ],
                        help_text='Opcional no MVP; útil para conciliação.',
                        max_length=20,
                        verbose_name='Meio',
                    ),
                ),
                (
                    'valor',
                    models.DecimalField(
                        decimal_places=2,
                        help_text='Sempre positivo; a natureza define se é entrada ou saída.',
                        max_digits=16,
                    ),
                ),
                ('data', models.DateField(db_index=True, verbose_name='Data')),
                ('descricao', models.CharField(max_length=500)),
                ('observacao', models.TextField(blank=True)),
                (
                    'caixa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='movimentos',
                        to='financeiro.caixa',
                    ),
                ),
                (
                    'empresa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='movimentos_caixa',
                        to='empresas.empresa',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Movimento de caixa',
                'verbose_name_plural': 'Movimentos de caixa',
                'ordering': ['-data', '-pk'],
            },
        ),
        migrations.AddConstraint(
            model_name='caixa',
            constraint=models.UniqueConstraint(
                condition=models.Q(tipo='geral'),
                fields=('empresa',),
                name='financeiro_caixa_unica_geral_por_empresa',
            ),
        ),
        migrations.AddConstraint(
            model_name='caixa',
            constraint=models.UniqueConstraint(
                condition=models.Q(tipo='obra', obra__isnull=False),
                fields=('empresa', 'obra'),
                name='financeiro_caixa_unica_obra_por_empresa',
            ),
        ),
        migrations.AddIndex(
            model_name='movimentocaixa',
            index=models.Index(fields=['empresa', 'data'], name='financeiro__empresa_16b4c2_idx'),
        ),
        migrations.AddIndex(
            model_name='movimentocaixa',
            index=models.Index(fields=['caixa', 'data'], name='financeiro__caixa_i_0b8b0f_idx'),
        ),
        migrations.RunPython(criar_caixa_geral_por_empresa, migrations.RunPython.noop),
    ]
