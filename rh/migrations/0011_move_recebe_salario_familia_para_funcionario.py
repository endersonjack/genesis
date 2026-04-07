# recebe_salario_familia passa a ser do Funcionario (não do Dependente).
# O histórico de migrações nunca incluiu esse campo em Dependente; só AddField em Funcionario.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0010_remove_valetransporte_empresa_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='funcionario',
            name='recebe_salario_familia',
            field=models.BooleanField(
                default=False,
                help_text='Salário família (INSS). Pode ser usado em relatórios e integrações futuras.',
                verbose_name='Recebe salário família',
            ),
        ),
    ]
