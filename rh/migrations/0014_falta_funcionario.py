from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0013_remove_dependente_recebe_salario_familia'),
    ]

    operations = [
        migrations.CreateModel(
            name='FaltaFuncionario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('tipo', models.CharField(choices=[('abonada', 'Abonada'), ('saude', 'Por saúde'), ('nao_justificada', 'Não justificada')], max_length=20)),
                ('data_inicio', models.DateField()),
                ('data_fim', models.DateField()),
                ('ausencia_parcial', models.BooleanField(default=False)),
                ('ausencia_parcial_descricao', models.CharField(blank=True, max_length=120)),
                ('motivo_descrito', models.TextField(blank=True)),
                ('anexo', models.FileField(blank=True, null=True, upload_to='rh/faltas/')),
                ('observacoes', models.TextField(blank=True)),
                ('funcionario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='faltas', to='rh.funcionario')),
            ],
            options={
                'verbose_name': 'Falta',
                'verbose_name_plural': 'Faltas',
                'ordering': ['-data_inicio', '-criado_em'],
            },
        ),
    ]

