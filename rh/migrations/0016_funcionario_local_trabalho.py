import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('local', '0002_local_latitude_longitude'),
        ('rh', '0015_falta_funcionario_subtipo'),
    ]

    operations = [
        migrations.AddField(
            model_name='funcionario',
            name='local_trabalho',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='funcionarios',
                to='local.local',
                verbose_name='Local de trabalho',
            ),
        ),
    ]

