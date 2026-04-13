"""Copiar cadastros (locais, fornecedores, clientes) para outra empresa do mesmo usuário."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from django import forms
from django.db.models import QuerySet
from django.http import HttpResponse

from empresas.models import Empresa

if TYPE_CHECKING:
    from clientes.models import Cliente
    from fornecedores.models import Fornecedor
    from local.models import Local


def empresas_destino_para_copia(user, empresa_origem: Empresa) -> QuerySet[Empresa]:
    if not user.is_authenticated or empresa_origem is None:
        return Empresa.objects.none()
    return (
        Empresa.objects.filter(
            usuarios_vinculados__usuario=user,
            usuarios_vinculados__ativo=True,
            ativa=True,
        )
        .exclude(pk=empresa_origem.pk)
        .distinct()
        .order_by('razao_social', 'nome_fantasia')
    )


class EscolherEmpresaDestinoForm(forms.Form):
    empresa_destino = forms.ModelChoiceField(
        label='Empresa de destino',
        queryset=Empresa.objects.none(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select rounded-3'}),
    )

    def __init__(self, *args, user=None, empresa_origem=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.empresa_origem = empresa_origem
        if user is not None and empresa_origem is not None:
            self.fields['empresa_destino'].queryset = empresas_destino_para_copia(
                user, empresa_origem
            )

    def clean_empresa_destino(self):
        dest = self.cleaned_data['empresa_destino']
        if self.empresa_origem and dest.pk == self.empresa_origem.pk:
            raise forms.ValidationError('Selecione uma empresa diferente da atual.')
        qs = empresas_destino_para_copia(self.user, self.empresa_origem)
        if not qs.filter(pk=dest.pk).exists():
            raise forms.ValidationError('Você não tem acesso a esta empresa.')
        return dest


def copiar_local_para_empresa(local: Local, destino: Empresa):
    from local.models import Local as LocalModel

    if LocalModel.objects.filter(empresa=destino, nome=local.nome).exists():
        raise ValueError(
            f'Já existe um local com o nome «{local.nome}» na empresa de destino.'
        )
    return LocalModel.objects.create(
        empresa=destino,
        nome=local.nome,
        endereco=local.endereco,
        link_maps=local.link_maps,
        link_maps_embed=local.link_maps_embed,
        latitude=local.latitude,
        longitude=local.longitude,
    )


def _resolver_categoria_fornecedor(origem_cat, destino: Empresa):
    from fornecedores.models import CategoriaFornecedor

    if origem_cat is None:
        return None
    cat, _ = CategoriaFornecedor.objects.get_or_create(
        empresa=destino,
        nome=origem_cat.nome,
    )
    return cat


def copiar_fornecedor_para_empresa(fornecedor: Fornecedor, destino: Empresa):
    from fornecedores.models import Fornecedor as FornecedorModel

    if FornecedorModel.objects.filter(
        empresa=destino, cpf_cnpj=fornecedor.cpf_cnpj
    ).exists():
        raise ValueError(
            'Já existe um fornecedor com o mesmo CPF/CNPJ na empresa de destino.'
        )
    cat = _resolver_categoria_fornecedor(fornecedor.categoria, destino)
    return FornecedorModel.objects.create(
        empresa=destino,
        tipo=fornecedor.tipo,
        categoria=cat,
        cpf_cnpj=fornecedor.cpf_cnpj,
        nome=fornecedor.nome,
        razao_social=fornecedor.razao_social,
        endereco=fornecedor.endereco,
        telefone_loja=fornecedor.telefone_loja,
        telefone_financeiro=fornecedor.telefone_financeiro,
        contato_financeiro=fornecedor.contato_financeiro,
        email=fornecedor.email,
        banco=fornecedor.banco,
        agencia=fornecedor.agencia,
        tipo_conta=fornecedor.tipo_conta,
        operacao=fornecedor.operacao,
        numero_conta=fornecedor.numero_conta,
        tipo_pix=fornecedor.tipo_pix,
        pix=fornecedor.pix,
    )


def copiar_cliente_para_empresa(cliente: Cliente, destino: Empresa):
    from clientes.models import Cliente as ClienteModel

    doc = (cliente.cpf_cnpj or '').strip()
    if doc and ClienteModel.objects.filter(empresa=destino, cpf_cnpj=doc).exists():
        raise ValueError(
            'Já existe um cliente com o mesmo CPF/CNPJ na empresa de destino.'
        )
    return ClienteModel.objects.create(
        empresa=destino,
        tipo=cliente.tipo,
        nome=cliente.nome,
        cpf_cnpj=cliente.cpf_cnpj,
        razao_social=cliente.razao_social,
        endereco=cliente.endereco,
        telefone=cliente.telefone,
        email=cliente.email,
    )


def _resolver_cliente_contratante_obra(cliente_origem, destino: Empresa):
    from clientes.models import Cliente

    if cliente_origem is None:
        return None
    doc = (cliente_origem.cpf_cnpj or '').strip()
    if doc:
        c = Cliente.objects.filter(empresa=destino, cpf_cnpj=doc).first()
        if c:
            return c
    return Cliente.objects.filter(empresa=destino, nome=cliente_origem.nome).first()


def copiar_obra_para_empresa(obra, destino: Empresa):
    from obras.models import Obra as ObraModel

    contr = _resolver_cliente_contratante_obra(obra.contratante, destino)
    if obra.contratante_id and contr is None:
        raise ValueError(
            'Não há cliente correspondente ao contratante na empresa de destino. '
            'Copie o cliente ou cadastre-o antes.'
        )
    return ObraModel.objects.create(
        empresa=destino,
        nome=obra.nome,
        contratante=contr,
        objeto=obra.objeto,
        endereco=obra.endereco,
        cno=obra.cno,
        valor=obra.valor,
        secretaria=obra.secretaria,
        gestor=obra.gestor,
        fiscal=obra.fiscal,
        data_inicio=obra.data_inicio,
        prazo=obra.prazo,
        data_fim=obra.data_fim,
    )


def resposta_htmx_copia_sucesso() -> HttpResponse:
    r = HttpResponse(status=200)
    r['HX-Trigger'] = json.dumps({'closeCopiarCadastroModal': True})
    return r
