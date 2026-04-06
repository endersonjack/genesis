from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from core.urlutils import redirect_empresa

from auditoria.registry import registrar_auditoria

from rh.views.base import _empresa_ativa_or_redirect

from .forms import EmpresaPreferenciasForm


@login_required
def preferencias(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(request)
    if redirect_response:
        return redirect_response

    if request.method == 'POST':
        form = EmpresaPreferenciasForm(
            request.POST,
            request.FILES,
            instance=empresa_ativa,
        )
        if form.is_valid():
            form.save()
            registrar_auditoria(
                request,
                acao='update',
                resumo=f'Preferências da empresa "{empresa_ativa}" atualizadas.',
                modulo='empresas',
            )
            messages.success(request, 'Preferências da empresa salvas.')
            return redirect_empresa(request, 'empresa_preferencias')
    else:
        form = EmpresaPreferenciasForm(instance=empresa_ativa)

    return render(
        request,
        'empresas/preferencias.html',
        {
            'form': form,
            'empresa': empresa_ativa,
        },
    )
