from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


@login_required
def home(request):
    if not request.session.get('empresa_id'):
        return redirect('selecionar_empresa')

    return render(request, 'dashboard/home.html')