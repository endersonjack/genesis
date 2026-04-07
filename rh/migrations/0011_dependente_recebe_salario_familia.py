# Ramo paralelo: campo em Dependente (depois consolidado em Funcionario na 0013).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0010_remove_valetransporte_empresa_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='dependente',
            name='recebe_salario_familia',
            field=models.BooleanField(
                default=False,
                help_text='Salário família (INSS). Pode ser usado em relatórios e integrações futuras.',
                verbose_name='Recebe salário família',
            ),
        ),
    ]
