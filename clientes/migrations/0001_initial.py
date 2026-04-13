import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('empresas', '0004_empresa_logo'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cliente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                (
                    'tipo',
                    models.CharField(
                        choices=[
                            ('PF', 'Pessoa Física'),
                            ('PJ', 'Pessoa Jurídica'),
                            ('AP', 'Administração Pública'),
                        ],
                        default='PJ',
                        max_length=2,
                    ),
                ),
                ('nome', models.CharField(max_length=200)),
                ('razao_social', models.CharField(blank=True, max_length=200)),
                ('endereco', models.CharField(blank=True, max_length=500, verbose_name='Endereço')),
                ('telefone', models.CharField(blank=True, max_length=20)),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='E-mail')),
                (
                    'empresa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='clientes',
                        to='empresas.empresa',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Cliente',
                'verbose_name_plural': 'Clientes',
                'ordering': ['nome'],
            },
        ),
    ]
