# Logo da empresa para PDFs e planilhas

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0003_empresa_recibos_preferencias'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='logo',
            field=models.ImageField(
                blank=True,
                help_text='PNG, JPG ou WebP. Usado no cabeçalho de recibos e exportações.',
                null=True,
                upload_to='empresas/logos/',
                verbose_name='Logo da empresa',
            ),
        ),
    ]
