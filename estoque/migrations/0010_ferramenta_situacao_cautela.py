from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0008_ferramenta'),
    ]

    operations = [
        migrations.AddField(
            model_name='ferramenta',
            name='situacao_cautela',
            field=models.CharField(
                'Situação na cautela',
                choices=[('livre', 'Livre'), ('ocupada', 'Ocupada')],
                db_index=True,
                default='livre',
                help_text=(
                    'Ferramenta fica OCUPADA enquanto estiver em cautela ativa e volta a '
                    'LIVRE quando for entregue.'
                ),
                max_length=10,
            ),
        ),
    ]
