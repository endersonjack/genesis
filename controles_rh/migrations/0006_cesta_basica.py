import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('controles_rh', '0005_valetransporteitem_valor_base'),
        ('rh', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CestaBasicaLista',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(blank=True, help_text='Opcional. Identificação na lista de controles.', max_length=120, verbose_name='Título interno')),
                ('texto_declaracao', models.TextField(blank=True, help_text='Vazio = texto padrão com o nome da empresa.', verbose_name='Texto da declaração')),
                ('data_emissao_recibo', models.DateField(blank=True, null=True, verbose_name='Data no rodapé do recibo')),
                ('local_emissao', models.CharField(blank=True, default='PARNAMIRIM - RN', max_length=120, verbose_name='Local (cidade/UF)')),
                ('observacao', models.TextField(blank=True, verbose_name='Observação interna')),
                ('ativa', models.BooleanField(default=True, verbose_name='Ativa')),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
                ('data_atualizacao', models.DateTimeField(auto_now=True)),
                ('competencia', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='cesta_basica', to='controles_rh.competencia')),
            ],
            options={
                'verbose_name': 'Lista de Cesta Básica',
                'verbose_name_plural': 'Listas de Cesta Básica',
            },
        ),
        migrations.CreateModel(
            name='CestaBasicaItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(blank=True, max_length=150, verbose_name='Empregado')),
                ('funcao', models.CharField(blank=True, max_length=120, verbose_name='Função')),
                ('lotacao', models.CharField(blank=True, max_length=120, verbose_name='Lotação')),
                ('ordem', models.PositiveIntegerField(default=0, verbose_name='Ordem')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
                ('data_atualizacao', models.DateTimeField(auto_now=True)),
                ('funcionario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='itens_cesta_basica', to='rh.funcionario')),
                ('lista', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='itens', to='controles_rh.cestabasicalista')),
            ],
            options={
                'verbose_name': 'Item de Cesta Básica',
                'verbose_name_plural': 'Itens de Cesta Básica',
                'ordering': ['ordem', 'nome', 'id'],
            },
        ),
    ]
