from django.db import migrations, models


def definir_primeira_como_padrao(apps, schema_editor):
    Item = apps.get_model('estoque', 'Item')
    ItemImagem = apps.get_model('estoque', 'ItemImagem')
    for item in Item.objects.all():
        imgs = list(
            ItemImagem.objects.filter(item=item).order_by('ordem', 'pk')
        )
        if not imgs:
            continue
        if any(getattr(im, 'padrao', False) for im in imgs):
            continue
        first = imgs[0]
        first.padrao = True
        first.save(update_fields=['padrao'])


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0012_motivodevolucaocautela_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='itemimagem',
            name='padrao',
            field=models.BooleanField(
                default=False,
                help_text='Imagem exibida nas listagens e buscas quando houver mais de uma.',
                verbose_name='Padrão para visualização',
            ),
        ),
        migrations.RunPython(
            definir_primeira_como_padrao,
            migrations.RunPython.noop,
        ),
    ]
