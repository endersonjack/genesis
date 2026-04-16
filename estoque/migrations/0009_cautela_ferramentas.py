import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('empresas', '0004_empresa_logo'),
        ('estoque', '0010_ferramenta_situacao_cautela'),
        ('local', '0001_initial'),
        ('obras', '0001_initial'),
        ('rh', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cautela',
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
                    'data_inicio_cautela',
                    models.DateField(verbose_name='Data início da cautela'),
                ),
                (
                    'data_fim',
                    models.DateField(blank=True, null=True, verbose_name='Data fim'),
                ),
                (
                    'situacao',
                    models.CharField(
                        choices=[
                            ('ativa', 'Ativa'),
                            ('inativa', 'Inativa'),
                        ],
                        db_index=True,
                        default='ativa',
                        max_length=10,
                        verbose_name='Situação',
                    ),
                ),
                (
                    'entrega',
                    models.CharField(
                        choices=[
                            ('nao', 'Não'),
                            ('parcial', 'Parcial'),
                            ('total', 'Total'),
                        ],
                        db_index=True,
                        default='nao',
                        help_text='Indica o andamento da devolução das ferramentas.',
                        max_length=10,
                        verbose_name='Entrega',
                    ),
                ),
                ('observacoes', models.TextField(blank=True, verbose_name='Obs.')),
                (
                    'almoxarife',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='cautelas_ferramentas_almoxarife',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'empresa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='cautelas_ferramentas',
                        to='empresas.empresa',
                    ),
                ),
                (
                    'funcionario',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='cautelas_ferramentas',
                        to='rh.funcionario',
                    ),
                ),
                (
                    'local',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='cautelas_ferramentas',
                        to='local.local',
                    ),
                ),
                (
                    'obra',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='cautelas_ferramentas',
                        to='obras.obra',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Cautela de ferramentas',
                'verbose_name_plural': 'Cautelas de ferramentas',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.CreateModel(
            name='Entrega_Cautela',
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
                            ('parcial', 'Parcial'),
                            ('completa', 'Completa'),
                        ],
                        db_index=True,
                        max_length=10,
                        verbose_name='Tipo',
                    ),
                ),
                (
                    'data_entrega',
                    models.DateField(verbose_name='Data da entrega'),
                ),
                ('observacoes', models.TextField(blank=True, verbose_name='Obs.')),
                (
                    'cautela',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='entregas',
                        to='estoque.cautela',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Entrega / devolução de cautela',
                'verbose_name_plural': 'Entregas / devoluções de cautelas',
                'ordering': ['-data_entrega', '-criado_em'],
            },
        ),
        migrations.AddField(
            model_name='cautela',
            name='ferramentas',
            field=models.ManyToManyField(
                blank=True,
                related_name='cautelas_ferramentas',
                to='estoque.ferramenta',
            ),
        ),
        migrations.AddIndex(
            model_name='cautela',
            index=models.Index(
                fields=['empresa', 'situacao'],
                name='idx_cautela_empresa_situacao',
            ),
        ),
        migrations.AddIndex(
            model_name='cautela',
            index=models.Index(
                fields=['empresa', 'entrega'],
                name='idx_cautela_empresa_entrega',
            ),
        ),
    ]
