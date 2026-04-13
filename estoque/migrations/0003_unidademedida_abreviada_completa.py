from django.db import migrations, models


def forwards_copiar_nome(apps, schema_editor):
    UnidadeMedida = apps.get_model('estoque', 'UnidadeMedida')
    for u in UnidadeMedida.objects.all():
        n = (getattr(u, 'nome', None) or '').strip()
        u.abreviada = (n[:32] if n else '—')[:32]
        u.completa = n if n else '—'
        u.save(update_fields=['abreviada', 'completa'])


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0002_unidademedida'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='unidademedida',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='unidademedida',
            name='abreviada',
            field=models.CharField(max_length=32, null=True, verbose_name='Medida abreviada'),
        ),
        migrations.AddField(
            model_name='unidademedida',
            name='completa',
            field=models.CharField(max_length=120, null=True, verbose_name='Medida completa'),
        ),
        migrations.RunPython(forwards_copiar_nome, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='unidademedida',
            name='nome',
        ),
        migrations.AlterField(
            model_name='unidademedida',
            name='abreviada',
            field=models.CharField(
                help_text='Ex.: Kg, m, UN',
                max_length=32,
                verbose_name='Medida abreviada',
            ),
        ),
        migrations.AlterField(
            model_name='unidademedida',
            name='completa',
            field=models.CharField(
                help_text='Ex.: Quilograma, Metro, Unidade',
                max_length=120,
                verbose_name='Medida completa',
            ),
        ),
        migrations.AlterModelOptions(
            name='unidademedida',
            options={
                'ordering': ['abreviada'],
                'verbose_name': 'Unidade de medida',
                'verbose_name_plural': 'Unidades de medida',
            },
        ),
        migrations.AlterUniqueTogether(
            name='unidademedida',
            unique_together={('empresa', 'abreviada')},
        ),
    ]
