from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

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
            messages.success(request, 'Preferências da empresa salvas.')
            return redirect('empresa_preferencias')
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
