import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('rh', '0013_remove_dependente_recebe_salario_familia'),
        ('controles_rh', '0014_valetransporteitem_dias_default_20'),
    ]

    operations = [
        migrations.CreateModel(
            name='AlteracaoFolhaLinha',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'hora_extra',
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=8,
                        verbose_name='Hora extra (h)',
                    ),
                ),
                (
                    'horas_feriado',
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=8,
                        verbose_name='Horas feriado (h)',
                    ),
                ),
                (
                    'adicional',
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        verbose_name='Adicional (R$)',
                    ),
                ),
                (
                    'premio',
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        verbose_name='Prêmio (R$)',
                    ),
                ),
                (
                    'outro_adicional',
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        verbose_name='Outro adicional (R$)',
                    ),
                ),
                (
                    'descontos',
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        verbose_name='Descontos (R$)',
                    ),
                ),
                (
                    'outro_desconto',
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        verbose_name='Outro desconto (R$)',
                    ),
                ),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
                ('data_atualizacao', models.DateTimeField(auto_now=True)),
                (
                    'competencia',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='alteracoes_folha',
                        to='controles_rh.competencia',
                    ),
                ),
                (
                    'funcionario',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='alteracoes_folha',
                        to='rh.funcionario',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Linha de alteração de folha',
                'verbose_name_plural': 'Linhas de alteração de folha',
                'ordering': ['funcionario__nome', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='alteracaofolhalinha',
            constraint=models.UniqueConstraint(
                fields=('competencia', 'funcionario'),
                name='unique_alteracao_folha_por_competencia_funcionario',
            ),
        ),
    ]
