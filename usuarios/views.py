from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import UsuarioEmpresa


@login_required
def selecionar_empresa(request):
    vinculos = UsuarioEmpresa.objects.filter(
        usuario=request.user,
        ativo=True,
        empresa__ativa=True
    ).select_related('empresa')

    if request.method == 'POST':
        empresa_id = request.POST.get('empresa_id')
        vinculo = get_object_or_404(
            UsuarioEmpresa,
            usuario=request.user,
            empresa_id=empresa_id,
            ativo=True,
            empresa__ativa=True
        )
        request.session['empresa_id'] = vinculo.empresa.id
        return redirect('dashboard_home', empresa_id=vinculo.empresa.id)

    return render(request, 'usuarios/selecionar_empresa.html', {
        'vinculos': vinculos
    }) 