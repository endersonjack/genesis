# Generated manually for preferências de recibo

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0002_empresa_cor_tema'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='endereco',
            field=models.CharField(
                blank=True,
                help_text='Exibido no cabeçalho dos recibos (junto com CNPJ e telefone).',
                max_length=500,
                verbose_name='Endereço',
            ),
        ),
        migrations.AddField(
            model_name='empresa',
            name='local_padrao_recibo',
            field=models.CharField(
                blank=True,
                help_text='Cidade/UF no rodapé quando a lista não define outro local.',
                max_length=120,
                verbose_name='Local padrão nos recibos',
            ),
        ),
        migrations.AddField(
            model_name='empresa',
            name='texto_declaracao_cesta_padrao',
            field=models.TextField(
                blank=True,
                help_text='Usado quando a lista deixa o texto da declaração em branco.',
                verbose_name='Texto da declaração (cesta básica)',
            ),
        ),
        migrations.AddField(
            model_name='empresa',
            name='rodape_extra_recibo',
            field=models.TextField(
                blank=True,
                help_text='Texto opcional abaixo da data e local (ex.: nota legal ou contato).',
                verbose_name='Observação no rodapé do recibo',
            ),
        ),
    ]
