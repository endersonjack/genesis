from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0006_requisicoes_estoque'),
    ]

    operations = [
        migrations.AddField(
            model_name='requisicaoestoque',
            name='status',
            field=models.CharField(
                choices=[('ativa', 'Ativa'), ('cancelada', 'Cancelada')],
                db_index=True,
                default='ativa',
                help_text=(
                    'No app, só é possível cancelar (com devolução ao estoque). '
                    'Reativar ou alterar situação manualmente no Admin não ajusta o estoque.'
                ),
                max_length=20,
                verbose_name='Situação',
            ),
        ),
        migrations.AddIndex(
            model_name='requisicaoestoque',
            index=models.Index(
                fields=['empresa', 'status', 'criado_em'],
                name='estoque_req_emp_st_cri_idx',
            ),
        ),
    ]
