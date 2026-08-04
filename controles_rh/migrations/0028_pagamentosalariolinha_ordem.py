# Generated manually for pagamento salario row ordering.
from django.db import migrations, models


def preencher_ordem_pagamento_salario(apps, schema_editor):
    PagamentoSalarioLinha = apps.get_model('controles_rh', 'PagamentoSalarioLinha')
    PagamentoSalarioControle = apps.get_model('controles_rh', 'PagamentoSalarioControle')

    for controle in PagamentoSalarioControle.objects.all().iterator():
        linhas = (
            PagamentoSalarioLinha.objects.filter(controle_id=controle.pk)
            .order_by('funcionario__nome', 'id')
            .values_list('id', flat=True)
        )
        for ordem, linha_id in enumerate(linhas, start=1):
            PagamentoSalarioLinha.objects.filter(pk=linha_id).update(ordem=ordem)


class Migration(migrations.Migration):

    dependencies = [
        ('controles_rh', '0027_valetransportepagamento'),
    ]

    operations = [
        migrations.AddField(
            model_name='pagamentosalariolinha',
            name='ordem',
            field=models.PositiveIntegerField(default=0, verbose_name='Ordem'),
        ),
        migrations.RunPython(preencher_ordem_pagamento_salario, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name='pagamentosalariolinha',
            options={
                'ordering': ['ordem', 'funcionario__nome', 'id'],
                'verbose_name': 'Linha de pagamento de salário',
                'verbose_name_plural': 'Linhas de pagamento de salário',
            },
        ),
    ]
