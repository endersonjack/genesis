# Une os dois ramos 0011 (dependente vs funcionário) num único histórico.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0011_dependente_recebe_salario_familia'),
        ('rh', '0011_move_recebe_salario_familia_para_funcionario'),
    ]

    operations = []
