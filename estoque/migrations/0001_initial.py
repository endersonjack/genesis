import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('empresas', '0004_empresa_logo'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoriaFerramenta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('nome', models.CharField(max_length=120)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='categorias_ferramenta', to='empresas.empresa')),
            ],
            options={
                'verbose_name': 'Categoria de ferramenta',
                'verbose_name_plural': 'Categorias de ferramentas',
                'ordering': ['nome'],
                'unique_together': {('empresa', 'nome')},
            },
        ),
        migrations.CreateModel(
            name='CategoriaItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('nome', models.CharField(max_length=120)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='categorias_item', to='empresas.empresa')),
            ],
            options={
                'verbose_name': 'Categoria de item',
                'verbose_name_plural': 'Categorias de itens',
                'ordering': ['nome'],
                'unique_together': {('empresa', 'nome')},
            },
        ),
    ]
