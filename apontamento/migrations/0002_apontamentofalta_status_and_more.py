# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apontamento', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='apontamentofalta',
            name='status',
            field=models.CharField(
                choices=[
                    ('pendente', 'Pendente'),
                    ('finalizado', 'Finalizado'),
                    ('arquivado', 'Arquivado'),
                ],
                db_index=True,
                default='pendente',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='apontamentoobservacaolocal',
            name='status',
            field=models.CharField(
                choices=[
                    ('pendente', 'Pendente'),
                    ('finalizado', 'Finalizado'),
                    ('arquivado', 'Arquivado'),
                ],
                db_index=True,
                default='pendente',
                max_length=20,
            ),
        ),
    ]
