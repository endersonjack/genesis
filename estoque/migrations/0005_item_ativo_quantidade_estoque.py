from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0004_item_itemimagem'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='quantidade_estoque',
            field=models.DecimalField(
                'Quantidade em estoque',
                decimal_places=4,
                default=0,
                help_text='Saldo atual. Movimentações futuras alterarão este valor.',
                max_digits=14,
            ),
        ),
        migrations.AddField(
            model_name='item',
            name='ativo',
            field=models.BooleanField(
                default=True,
                help_text='Itens inativos não entram em movimentação nem nas buscas operacionais.',
            ),
        ),
    ]
