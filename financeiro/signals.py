"""Garante caixa geral ao criar nova empresa."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from empresas.models import Empresa

from .models import Caixa


@receiver(post_save, sender=Empresa)
def garantir_caixa_geral_ao_criar_empresa(sender, instance, created, **kwargs):
    if not created:
        return
    Caixa.objects.get_or_create(
        empresa=instance,
        tipo=Caixa.Tipo.GERAL,
        defaults={'nome': 'Caixa geral', 'ativo': True},
    )
