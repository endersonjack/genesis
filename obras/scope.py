from __future__ import annotations

from django import forms
from django.db.models import Q
from django.utils import timezone

from usuarios.models import UsuarioEmpresa

from .models import Obra


def obras_empresa_ids(request, empresa) -> list[int]:
    if not empresa:
        return []
    if not getattr(request, 'usuario_obras_empresas_acessiveis', False):
        return [empresa.pk]
    ids = list(
        UsuarioEmpresa.objects.filter(
            usuario=request.user,
            ativo=True,
            obras=True,
            empresa__ativa=True,
        ).values_list('empresa_id', flat=True)
    )
    return ids or [empresa.pk]


def obras_queryset(request, empresa):
    ids = obras_empresa_ids(request, empresa)
    return (
        Obra.objects.filter(empresa_id__in=ids)
        .select_related('contratante', 'empresa')
        .order_by('empresa__razao_social', 'empresa__nome_fantasia', 'nome')
    )


def obra_empresa_label(obra, empresa_ativa) -> str:
    if not obra or not empresa_ativa or obra.empresa_id == empresa_ativa.pk:
        return ''
    return (
        getattr(obra.empresa, 'nome_fantasia', '')
        or getattr(obra.empresa, 'razao_social', '')
        or str(obra.empresa)
    )


def obra_label(obra, empresa_ativa) -> str:
    label = str(obra)
    empresa_label = obra_empresa_label(obra, empresa_ativa)
    if empresa_label:
        label = f'{label} · {empresa_label}'
    return label


def obras_ativas_queryset(request, empresa):
    hoje = timezone.localdate()
    return obras_queryset(request, empresa).filter(
        Q(data_fim__isnull=True) | Q(data_fim__gte=hoje)
    )


class ObraEmpresaChoiceField(forms.ModelChoiceField):
    def __init__(self, *args, empresa_ativa=None, **kwargs):
        self.empresa_ativa = empresa_ativa
        super().__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        return obra_label(obj, self.empresa_ativa)


def aplicar_obra_labels(obras, empresa_ativa):
    for obra in obras:
        obra.autocomplete_label = obra_label(obra, empresa_ativa)
    return obras


def aplicar_obra_labels_em_objetos(objetos, empresa_ativa, attr='obra'):
    for obj in objetos:
        obra = getattr(obj, attr, None)
        if obra:
            obra.autocomplete_label = obra_label(obra, empresa_ativa)
    return objetos
