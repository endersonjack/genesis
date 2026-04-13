import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnidadeMedida',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('nome', models.CharField(max_length=120)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='unidades_medida', to='empresas.empresa')),
            ],
            options={
                'verbose_name': 'Unidade de medida',
                'verbose_name_plural': 'Unidades de medida',
                'ordering': ['nome'],
                'unique_together': {('empresa', 'nome')},
            },
        ),
    ]
