import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('empresas', '0004_empresa_logo'),
        ('rh', '0016_funcionario_local_trabalho'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoriaFornecedor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('nome', models.CharField(max_length=120)),
                (
                    'empresa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='categorias_fornecedor',
                        to='empresas.empresa',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Categoria de fornecedor',
                'verbose_name_plural': 'Categorias de fornecedor',
                'ordering': ['nome'],
                'unique_together': {('empresa', 'nome')},
            },
        ),
        migrations.CreateModel(
            name='Fornecedor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                (
                    'tipo',
                    models.CharField(
                        choices=[('PF', 'Pessoa Física'), ('PJ', 'Pessoa Jurídica')],
                        default='PJ',
                        max_length=2,
                    ),
                ),
                (
                    'cpf_cnpj',
                    models.CharField(
                        help_text='Apenas números (11 ou 14 dígitos).',
                        max_length=14,
                        verbose_name='CPF/CNPJ',
                    ),
                ),
                ('nome', models.CharField(max_length=200)),
                ('razao_social', models.CharField(blank=True, max_length=200)),
                ('endereco', models.CharField(blank=True, max_length=500, verbose_name='Endereço')),
                ('telefone_loja', models.CharField(blank=True, max_length=20, verbose_name='Telefone (loja)')),
                (
                    'telefone_financeiro',
                    models.CharField(blank=True, max_length=20, verbose_name='Telefone (financeiro)'),
                ),
                (
                    'contato_financeiro',
                    models.CharField(
                        blank=True,
                        help_text='Nome da pessoa no financeiro.',
                        max_length=150,
                        verbose_name='Contato financeiro',
                    ),
                ),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='E-mail')),
                ('agencia', models.CharField(blank=True, max_length=20)),
                (
                    'tipo_conta',
                    models.CharField(
                        blank=True,
                        choices=[
                            ('', '---------'),
                            ('corrente', 'Conta Corrente'),
                            ('poupanca', 'Conta Poupança'),
                            ('salario', 'Conta Salário'),
                        ],
                        max_length=20,
                    ),
                ),
                ('operacao', models.CharField(blank=True, max_length=20)),
                ('numero_conta', models.CharField(blank=True, max_length=30)),
                (
                    'tipo_pix',
                    models.CharField(
                        blank=True,
                        choices=[
                            ('', '---------'),
                            ('cpf', 'CPF'),
                            ('email', 'E-mail'),
                            ('telefone', 'Telefone'),
                            ('aleatoria', 'Chave Aleatória'),
                        ],
                        max_length=20,
                    ),
                ),
                ('pix', models.CharField(blank=True, max_length=150)),
                (
                    'banco',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='fornecedores',
                        to='rh.banco',
                    ),
                ),
                (
                    'categoria',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='fornecedores',
                        to='fornecedores.categoriafornecedor',
                    ),
                ),
                (
                    'empresa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='fornecedores',
                        to='empresas.empresa',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Fornecedor',
                'verbose_name_plural': 'Fornecedores',
                'ordering': ['nome'],
                'unique_together': {('empresa', 'cpf_cnpj')},
            },
        ),
    ]
