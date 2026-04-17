from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auditoria', '0001_initial'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='registroauditoria',
            new_name='auditoria_r_empresa_fdd847_idx',
            old_name='auditoria_r_empresa_criado_idx',
        ),
    ]
