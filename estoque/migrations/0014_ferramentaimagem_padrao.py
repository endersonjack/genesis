from django.db import migrations, models


def definir_primeira_como_padrao(apps, schema_editor):
    Ferramenta = apps.get_model('estoque', 'Ferramenta')
    FerramentaImagem = apps.get_model('estoque', 'FerramentaImagem')
    for ferr in Ferramenta.objects.all():
        imgs = list(
            FerramentaImagem.objects.filter(ferramenta=ferr).order_by('ordem', 'pk')
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
        ('estoque', '0013_itemimagem_padrao'),
    ]

    operations = [
        migrations.AddField(
            model_name='ferramentaimagem',
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
