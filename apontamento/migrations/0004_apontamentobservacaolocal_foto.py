# Generated manually for foto field on ApontamentoObservacaoLocal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apontamento', '0003_status_alterado_audit_e_visto'),
    ]

    operations = [
        migrations.AddField(
            model_name='apontamentoobservacaolocal',
            name='foto',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='apontamento/anotacoes/',
                verbose_name='Foto (anexo)',
            ),
        ),
    ]
