# Une as duas migrações 0004 que partiam de 0003 (campo foto vs modelo Fotos).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('apontamento', '0004_apontamentobservacaolocal_foto'),
        ('apontamento', '0004_apontamentoobservacaofoto'),
    ]

    operations = []
