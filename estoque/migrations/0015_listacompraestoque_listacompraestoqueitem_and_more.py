import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('estoque', '0014_ferramentaimagem_padrao'),
    ]

    operations = [
        migrations.CreateModel(
            name='ListaCompraEstoque',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('data_pedido', models.DateField(verbose_name='Data do pedido')),
                ('status', models.CharField(choices=[('rascunho', 'Rascunho'), ('solicitado', 'Solicitado'), ('comprado', 'Comprado')], db_index=True, default='rascunho', max_length=20)),
                ('observacoes', models.TextField(blank=True, verbose_name='Observações gerais')),
                ('criado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='listas_compra_estoque_criadas', to=settings.AUTH_USER_MODEL)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='listas_compra_estoque', to='empresas.empresa')),
            ],
            options={
                'verbose_name': 'Lista de compra (estoque)',
                'verbose_name_plural': 'Listas de compra (estoque)',
                'ordering': ['-data_pedido', '-pk'],
            },
        ),
        migrations.CreateModel(
            name='ListaCompraEstoqueItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantidade_comprar', models.DecimalField(decimal_places=4, default=0, max_digits=14, verbose_name='Quantidade a comprar')),
                ('observacoes', models.TextField(blank=True, verbose_name='Observações do item')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='linhas_lista_compra_estoque', to='estoque.item')),
                ('lista', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='itens', to='estoque.listacompraestoque')),
            ],
            options={
                'verbose_name': 'Item da lista de compra',
                'verbose_name_plural': 'Itens da lista de compra',
                'ordering': ['pk'],
            },
        ),
        migrations.AddIndex(
            model_name='listacompraestoque',
            index=models.Index(fields=['empresa', 'data_pedido'], name='estoque_lis_empresa_16e0f3_idx'),
        ),
        migrations.AddIndex(
            model_name='listacompraestoque',
            index=models.Index(fields=['empresa', 'status', 'data_pedido'], name='estoque_lis_empresa_0a3f7d_idx'),
        ),
        migrations.AddConstraint(
            model_name='listacompraestoqueitem',
            constraint=models.UniqueConstraint(fields=('lista', 'item'), name='uniq_lista_compra_item'),
        ),
    ]
