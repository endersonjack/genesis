from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='cpf_cnpj',
            field=models.CharField(
                blank=True,
                help_text='Apenas números (11 ou 14 dígitos), conforme o tipo.',
                max_length=14,
                verbose_name='CPF/CNPJ',
            ),
        ),
        migrations.AddConstraint(
            model_name='cliente',
            constraint=models.UniqueConstraint(
                condition=~Q(cpf_cnpj=''),
                fields=('empresa', 'cpf_cnpj'),
                name='cliente_empresa_cpf_cnpj_uniq_nonempty',
            ),
        ),
    ]
