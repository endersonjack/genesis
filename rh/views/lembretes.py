"""
Views de lembretes do módulo RH.

Responsabilidades deste arquivo:
- listar lembretes do RH
- criar lembrete
- editar lembrete
- excluir lembrete

Observação:
- o calendário e dashboard apenas consomem esses lembretes
- o CRUD fica centralizado aqui
"""

from django.shortcuts import get_object_or_404, render

from auditoria.registry import audit_rh

from ..forms import LembreteRHForm
from ..models import LembreteRH
from .base import _empresa_ativa_or_redirect


# ==========================================================
# LISTA DE LEMBRETES
# ==========================================================
def lista_lembretes_rh(request):
    """
    Exibe a página principal de lembretes do RH.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para visualizar os lembretes.'
    )
    if redirect_response:
        return redirect_response

    lembretes = LembreteRH.objects.filter(
        empresa=empresa_ativa
    ).select_related('funcionario').order_by('data', 'titulo')

    return render(
        request,
        'rh/lembretes/lista.html',
        {
            'lembretes': lembretes,
        }
    )


# ==========================================================
# CRIAR LEMBRETE
# ==========================================================
def criar_lembrete_rh(request):
    """
    Cria um novo lembrete do RH.

    Em POST válido:
    - salva o lembrete
    - retorna a partial da lista atualizada
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de criar lembretes.'
    )
    if redirect_response:
        return redirect_response

    if request.method == 'POST':
        form = LembreteRHForm(request.POST, empresa_ativa=empresa_ativa)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa_ativa
            obj.save()

            audit_rh(
                request,
                'create',
                f'Lembrete "{obj.titulo}" criado.',
                {'lembrete_id': obj.pk},
            )
            lembretes = LembreteRH.objects.filter(
                empresa=empresa_ativa
            ).select_related('funcionario').order_by('data', 'titulo')

            return render(
                request,
                'rh/partials/lembretes_lista.html',
                {
                    'lembretes': lembretes,
                }
            )
    else:
        form = LembreteRHForm(empresa_ativa=empresa_ativa)

    return render(
        request,
        'rh/lembretes/form.html',
        {
            'form': form,
        }
    )


# ==========================================================
# EDITAR LEMBRETE
# ==========================================================
def editar_lembrete_rh(request, pk):
    """
    Edita um lembrete existente da empresa ativa.

    Em POST válido:
    - salva alterações
    - retorna a partial da lista atualizada
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de editar lembretes.'
    )
    if redirect_response:
        return redirect_response

    lembrete = get_object_or_404(
        LembreteRH,
        pk=pk,
        empresa=empresa_ativa,
    )

    if request.method == 'POST':
        form = LembreteRHForm(
            request.POST,
            instance=lembrete,
            empresa_ativa=empresa_ativa,
        )
        if form.is_valid():
            salvo = form.save()
            audit_rh(
                request,
                'update',
                f'Lembrete "{salvo.titulo}" atualizado.',
                {'lembrete_id': salvo.pk},
            )
            lembretes = LembreteRH.objects.filter(
                empresa=empresa_ativa
            ).select_related('funcionario').order_by('data', 'titulo')

            return render(
                request,
                'rh/partials/lembretes_lista.html',
                {
                    'lembretes': lembretes,
                }
            )
    else:
        form = LembreteRHForm(
            instance=lembrete,
            empresa_ativa=empresa_ativa,
        )

    return render(
        request,
        'rh/lembretes/form.html',
        {
            'form': form,
            'lembrete': lembrete,
        }
    )


# ==========================================================
# EXCLUIR LEMBRETE
# ==========================================================
def excluir_lembrete_rh(request, pk):
    """
    Exclui um lembrete da empresa ativa
    e retorna a partial com a lista atualizada.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de excluir lembretes.'
    )
    if redirect_response:
        return redirect_response

    lembrete = get_object_or_404(
        LembreteRH,
        pk=pk,
        empresa=empresa_ativa,
    )

    titulo = lembrete.titulo
    lid = lembrete.pk
    lembrete.delete()
    audit_rh(
        request,
        'delete',
        f'Lembrete "{titulo}" excluído.',
        {'lembrete_id': lid},
    )

    lembretes = LembreteRH.objects.filter(
        empresa=empresa_ativa
    ).select_related('funcionario').order_by('data', 'titulo')

    return render(
        request,
        'rh/partials/lembretes_lista.html',
        {
            'lembretes': lembretes,
        }
    )