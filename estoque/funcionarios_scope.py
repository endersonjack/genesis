from __future__ import annotations

from django import forms

from rh.models import Funcionario
from usuarios.models import UsuarioEmpresa


def estoque_funcionarios_empresa_ids(request, empresa) -> list[int]:
    if not empresa:
        return []
    if not getattr(request, 'usuario_estoque_funcionarios_empresas_acessiveis', False):
        return [empresa.pk]
    ids = list(
        UsuarioEmpresa.objects.filter(
            usuario=request.user,
            ativo=True,
            empresa__ativa=True,
        ).values_list('empresa_id', flat=True)
    )
    return ids or [empresa.pk]


def funcionarios_estoque_queryset(request, empresa, *, somente_ativos=True):
    ids = estoque_funcionarios_empresa_ids(request, empresa)
    qs = Funcionario.objects.filter(empresa_id__in=ids).select_related('empresa')
    if somente_ativos:
        qs = qs.exclude(situacao_atual__in=['demitido', 'inativo'])
    return qs.order_by('nome', 'empresa__nome_fantasia', 'empresa__razao_social')


def funcionario_estoque_label(funcionario, empresa_ativa) -> str:
    label = str(funcionario)
    if empresa_ativa and funcionario.empresa_id != empresa_ativa.pk:
        empresa_nome = (
            getattr(funcionario.empresa, 'nome_fantasia', '')
            or getattr(funcionario.empresa, 'razao_social', '')
            or str(funcionario.empresa)
        )
        label = f'{label} · {empresa_nome}'
    return label


class EstoqueFuncionarioChoiceField(forms.ModelChoiceField):
    def __init__(self, *args, empresa_ativa=None, **kwargs):
        self.empresa_ativa = empresa_ativa
        super().__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        return funcionario_estoque_label(obj, self.empresa_ativa)


def aplicar_autocomplete_labels(funcionarios, empresa_ativa):
    for funcionario in funcionarios:
        funcionario.autocomplete_label = funcionario_estoque_label(
            funcionario,
            empresa_ativa,
        )
    return funcionarios
