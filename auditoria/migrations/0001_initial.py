import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('empresas', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RegistroAuditoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('acao', models.CharField(choices=[('create', 'Criação'), ('update', 'Alteração'), ('delete', 'Exclusão'), ('export', 'Exportação'), ('other', 'Outro')], db_index=True, max_length=20)),
                ('modulo', models.CharField(blank=True, help_text='Identificador curto do app ou área (ex.: empresas, rh).', max_length=80)),
                ('resumo', models.CharField(max_length=255)),
                ('detalhes', models.JSONField(blank=True, default=dict)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='registros_auditoria', to='empresas.empresa')),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='registros_auditoria', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Registro de auditoria',
                'verbose_name_plural': 'Registros de auditoria',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.AddIndex(
            model_name='registroauditoria',
            index=models.Index(fields=['empresa', 'criado_em'], name='auditoria_r_empresa_criado_idx'),
        ),
    ]
