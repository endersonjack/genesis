from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from auditoria.registry import audit_controles_rh

from core.urlutils import redirect_empresa, reverse_empresa

from controles_rh.forms import AnexoDiversoCompetenciaForm
from controles_rh.models import AnexoDiversoCompetencia
from controles_rh.views.competencias import _get_competencia_empresa


def _is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def _get_anexo_diverso_empresa(request, pk):
    empresa_ativa = getattr(request, 'empresa_ativa', None)
    qs = AnexoDiversoCompetencia.objects.select_related(
        'competencia',
        'competencia__empresa',
        'usuario',
    )
    if empresa_ativa:
        qs = qs.filter(competencia__empresa=empresa_ativa)
    else:
        qs = qs.none()
    return get_object_or_404(qs, pk=pk)


@login_required
def criar_anexo_diverso(request, competencia_pk):
    competencia = _get_competencia_empresa(request, competencia_pk)

    if request.method == 'POST':
        form = AnexoDiversoCompetenciaForm(
            request.POST,
            request.FILES,
            competencia=competencia,
            usuario=request.user,
        )
        if form.is_valid():
            anexo = form.save()
            audit_controles_rh(
                request,
                'create',
                f'Anexo diverso "{anexo.nome}" adicionado.',
                {
                    'anexo_diverso_id': anexo.pk,
                    'competencia_id': competencia.pk,
                },
            )
            messages.success(request, f'Anexo "{anexo.nome}" adicionado com sucesso.')

            url = reverse_empresa(
                request,
                'controles_rh:detalhe_competencia',
                kwargs={'ano': competencia.ano, 'mes': competencia.mes},
            )
            if _is_htmx(request):
                response = HttpResponse(status=200)
                response['HX-Redirect'] = url
                return response
            return redirect_empresa(
                request,
                'controles_rh:detalhe_competencia',
                kwargs={'ano': competencia.ano, 'mes': competencia.mes},
            )

        messages.error(request, 'Não foi possível adicionar o anexo. Revise os campos.')
    else:
        form = AnexoDiversoCompetenciaForm(
            competencia=competencia,
            usuario=request.user,
        )

    return render(
        request,
        'controles_rh/competencias/_form_anexo_diverso_modal.html',
        {
            'competencia': competencia,
            'form': form,
        },
    )


@login_required
def excluir_anexo_diverso(request, pk):
    anexo = _get_anexo_diverso_empresa(request, pk)
    competencia = anexo.competencia

    if request.method == 'POST':
        nome = anexo.nome
        aid = anexo.pk
        anexo.delete()
        audit_controles_rh(
            request,
            'delete',
            f'Anexo diverso "{nome}" excluído.',
            {
                'anexo_diverso_id': aid,
                'competencia_id': competencia.pk,
            },
        )
        messages.success(request, f'Anexo "{nome}" excluído com sucesso.')

        url = reverse_empresa(
            request,
            'controles_rh:detalhe_competencia',
            kwargs={'ano': competencia.ano, 'mes': competencia.mes},
        )
        if _is_htmx(request):
            response = HttpResponse(status=200)
            response['HX-Redirect'] = url
            return response
        return redirect_empresa(
            request,
            'controles_rh:detalhe_competencia',
            kwargs={'ano': competencia.ano, 'mes': competencia.mes},
        )

    return render(
        request,
        'controles_rh/competencias/_excluir_anexo_diverso_modal.html',
        {
            'anexo': anexo,
            'competencia': competencia,
        },
    )
