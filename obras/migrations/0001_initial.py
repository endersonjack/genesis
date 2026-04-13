import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('clientes', '0002_cliente_cpf_cnpj'),
    ]

    operations = [
        migrations.CreateModel(
            name='Obra',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('nome', models.CharField(max_length=200, verbose_name='Nome da obra')),
                ('objeto', models.TextField(blank=True, verbose_name='Objeto')),
                ('endereco', models.CharField(blank=True, max_length=500, verbose_name='Endereço')),
                ('cno', models.CharField(blank=True, help_text='Cadastro Nacional de Obras (quando aplicável).', max_length=30, verbose_name='CNO')),
                ('valor', models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True, verbose_name='Valor (R$)')),
                ('secretaria', models.CharField(blank=True, max_length=200, verbose_name='Secretaria')),
                ('gestor', models.CharField(blank=True, max_length=200, verbose_name='Gestor')),
                ('fiscal', models.CharField(blank=True, max_length=200, verbose_name='Fiscal')),
                ('data_inicio', models.DateField(blank=True, null=True, verbose_name='Início')),
                ('prazo', models.CharField(blank=True, help_text='Ex.: 6 meses, 12 meses…', max_length=120, verbose_name='Prazo')),
                ('data_fim', models.DateField(blank=True, null=True, verbose_name='Fim')),
                ('contratante', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='obras', to='clientes.cliente', verbose_name='Contratante')),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='obras', to='empresas.empresa')),
            ],
            options={
                'verbose_name': 'Obra',
                'verbose_name_plural': 'Obras',
                'ordering': ['nome'],
            },
        ),
    ]
