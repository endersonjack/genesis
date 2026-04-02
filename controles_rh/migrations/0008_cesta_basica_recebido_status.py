from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('controles_rh', '0007_cestabasicalista_varias_por_competencia'),
    ]

    operations = [
        migrations.AddField(
            model_name='cestabasicalista',
            name='cb_calculo_automatico',
            field=models.BooleanField(
                default=True,
                help_text='Quando ativo, o status é calculado pelos checkboxes “Recebeu” nas linhas.',
                verbose_name='Status de entrega automático',
            ),
        ),
        migrations.AddField(
            model_name='cestabasicalista',
            name='cb_status_manual',
            field=models.CharField(
                blank=True,
                choices=[
                    ('falta_entregar', 'Falta entregar'),
                    ('entregue_totalmente', 'Entregue totalmente'),
                ],
                max_length=30,
                null=True,
                help_text='Usado apenas quando o status automático está desligado.',
                verbose_name='Status de entrega manual',
            ),
        ),
        migrations.AddField(
            model_name='cestabasicaitem',
            name='recebido',
            field=models.BooleanField(
                default=False,
                help_text='Marque quando a cesta já foi entregue a este empregado.',
                verbose_name='Recebeu',
            ),
        ),
    ]
