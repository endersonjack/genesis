# Após o merge: o dado passa a ser só do Funcionario (modelo atual).

from django.db import migrations, models


def forwards_copy_to_funcionario(apps, schema_editor):
    Dependente = apps.get_model('rh', 'Dependente')
    Funcionario = apps.get_model('rh', 'Funcionario')
    for dep in Dependente.objects.filter(recebe_salario_familia=True):
        Funcionario.objects.filter(pk=dep.funcionario_id).update(recebe_salario_familia=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0012_merge_salario_familia_branches'),
    ]

    operations = [
        migrations.RunPython(forwards_copy_to_funcionario, noop_reverse),
        migrations.RemoveField(
            model_name='dependente',
            name='recebe_salario_familia',
        ),
    ]
