from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from auditoria.models import RegistroAuditoria
from core.urlutils import redirect_empresa
from empresas.models import Empresa
from usuarios.models import Usuario, UsuarioEmpresa

from .forms import NotaAutoadesivaForm
from .models import NotaAutoadesiva


MESES = [
    (1, 'Janeiro'),
    (2, 'Fevereiro'),
    (3, 'Março'),
    (4, 'Abril'),
    (5, 'Maio'),
    (6, 'Junho'),
    (7, 'Julho'),
    (8, 'Agosto'),
    (9, 'Setembro'),
    (10, 'Outubro'),
    (11, 'Novembro'),
    (12, 'Dezembro'),
]


def _empresas_dashboard_qs(user):
    if user.is_superuser:
        return Empresa.objects.filter(ativa=True).order_by('razao_social')
    return (
        Empresa.objects.filter(
            usuarios_vinculados__usuario=user,
            usuarios_vinculados__ativo=True,
            ativa=True,
        )
        .distinct()
        .order_by('razao_social')
    )


def _usuarios_responsaveis_qs(empresas_qs, *usuarios_extras):
    usuarios_qs = (
        Usuario.objects.filter(
            Q(
                is_active=True,
                vinculos_empresa__empresa__in=empresas_qs,
                vinculos_empresa__ativo=True,
            )
            | Q(pk__in=[usuario.pk for usuario in usuarios_extras if usuario])
        )
        .distinct()
        .order_by('nome_completo', 'username')
    )
    return usuarios_qs


def _nota_text_color(hex_color):
    color = (hex_color or '').strip().lstrip('#')
    if len(color) != 6:
        return '#0f172a'
    try:
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
    except ValueError:
        return '#0f172a'
    luminance = (0.299 * r + 0.587 * g + 0.114 * b)
    return '#ffffff' if luminance < 150 else '#0f172a'


def _nota_gradient_end(hex_color):
    color = (hex_color or '').strip().lstrip('#')
    if len(color) != 6:
        return '#fff7cc'
    try:
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
    except ValueError:
        return '#fff7cc'
    r = int(r + (255 - r) * 0.38)
    g = int(g + (255 - g) * 0.38)
    b = int(b + (255 - b) * 0.38)
    return f'#{r:02x}{g:02x}{b:02x}'


def _decorar_notas(notas):
    for nota in notas:
        cor = getattr(nota, 'cor', '') or '#facc15'
        nota.bg_color = cor
        nota.bg_color_end = _nota_gradient_end(cor)
        nota.text_color = _nota_text_color(cor)
        responsaveis = list(nota.responsaveis.all())
        if not responsaveis and nota.responsavel_id:
            responsaveis = [nota.responsavel]
        nota.responsaveis_display = ', '.join(
            responsavel.nome_completo or responsavel.username for responsavel in responsaveis
        )
        nota.responsaveis_ids = [responsavel.pk for responsavel in responsaveis]
    return notas


def _notas_visiveis_qs(user, empresas_qs):
    return (
        NotaAutoadesiva.objects.filter(empresa__in=empresas_qs)
        .filter(Q(autor=user) | Q(responsavel=user) | Q(responsaveis=user))
        .distinct()
        .select_related('empresa', 'autor', 'responsavel')
        .prefetch_related('responsaveis')
        .order_by('concluida', '-criada_em')
    )


def _int_param(value, default, minimo=None, maximo=None):
    try:
        numero = int(value)
    except (TypeError, ValueError):
        return default
    if minimo is not None and numero < minimo:
        return default
    if maximo is not None and numero > maximo:
        return default
    return numero


@login_required
def home(request):
    context = {}
    empresa = getattr(request, 'empresa_ativa', None)
    if empresa:
        pode_ver_todos = bool(
            getattr(request, 'usuario_admin_empresa', False) or request.user.is_superuser
        )
        qs = (
            RegistroAuditoria.objects.filter(empresa=empresa)
            .select_related('usuario')
            .order_by('-criado_em')
        )
        if not pode_ver_todos:
            qs = qs.filter(usuario=request.user)
        context['ultimas_auditoria'] = list(qs[:20])
        context['auditoria_resumo_admin'] = pode_ver_todos

        empresas_qs = _empresas_dashboard_qs(request.user)
        usuarios_qs = _usuarios_responsaveis_qs(empresas_qs, request.user)
        initial_empresa = empresa if empresa.pk in list(empresas_qs.values_list('pk', flat=True)) else None
        notas_qs = _notas_visiveis_qs(request.user, empresas_qs)
        context.update(
            {
                'nota_form': NotaAutoadesivaForm(
                    empresas_qs=empresas_qs,
                    usuarios_qs=usuarios_qs,
                    initial={
                        'empresa': initial_empresa,
                        'cor': '#facc15',
                    },
                ),
                'notas_abertas': _decorar_notas(list(notas_qs.filter(concluida=False)[:60])),
                'usuarios_responsaveis': usuarios_qs,
            }
        )
    return render(request, 'dashboard/home.html', context)


@login_required
def notas_concluidas(request):
    hoje = timezone.localdate()
    mes = _int_param(request.GET.get('mes'), hoje.month, 1, 12)
    ano = _int_param(request.GET.get('ano'), hoje.year, 2000, hoje.year + 1)
    empresas_qs = _empresas_dashboard_qs(request.user)
    notas_qs = _notas_visiveis_qs(request.user, empresas_qs).filter(
        concluida=True,
        atualizada_em__year=ano,
        atualizada_em__month=mes,
    ).order_by('-atualizada_em')
    anos_com_notas = list(
        _notas_visiveis_qs(request.user, empresas_qs)
        .filter(concluida=True)
        .dates('atualizada_em', 'year', order='DESC')
    )
    anos = sorted({data.year for data in anos_com_notas} | {hoje.year, ano}, reverse=True)
    context = {
        'notas': _decorar_notas(list(notas_qs[:200])),
        'mes': mes,
        'ano': ano,
        'meses': MESES,
        'anos': anos,
    }
    return render(request, 'dashboard/notas_concluidas.html', context)


@login_required
@require_POST
def criar_nota(request):
    empresas_qs = _empresas_dashboard_qs(request.user)
    usuarios_qs = _usuarios_responsaveis_qs(empresas_qs, request.user)
    form = NotaAutoadesivaForm(
        request.POST,
        request.FILES,
        empresas_qs=empresas_qs,
        usuarios_qs=usuarios_qs,
    )
    if form.is_valid():
        nota = form.save(commit=False)
        nota.autor = request.user
        responsaveis = list(form.cleaned_data['responsaveis'])
        if request.user not in responsaveis:
            responsaveis.insert(0, request.user)
        nota.responsavel = responsaveis[0] if responsaveis else None
        nota.save()
        form.save_m2m()
        nota.responsaveis.add(request.user)
        messages.success(request, 'Nota criada.')
    else:
        messages.error(request, 'Não foi possível criar a nota. Revise os campos.')
    return redirect_empresa(request, 'dashboard_home')


def _get_nota_visivel(request, pk):
    empresas_qs = _empresas_dashboard_qs(request.user)
    return get_object_or_404(_notas_visiveis_qs(request.user, empresas_qs), pk=pk)


@login_required
@require_POST
def editar_nota(request, pk):
    nota = _get_nota_visivel(request, pk)
    if nota.autor_id != request.user.pk and not request.user.is_superuser:
        messages.error(request, 'Apenas quem criou a nota pode editá-la.')
        return redirect_empresa(request, 'dashboard_home')

    empresas_qs = _empresas_dashboard_qs(request.user)
    usuarios_qs = _usuarios_responsaveis_qs(empresas_qs, nota.autor)
    form = NotaAutoadesivaForm(
        request.POST,
        request.FILES,
        instance=nota,
        empresas_qs=empresas_qs,
        usuarios_qs=usuarios_qs,
    )
    if form.is_valid():
        nota = form.save(commit=False)
        responsaveis = list(form.cleaned_data['responsaveis'])
        if nota.autor not in responsaveis:
            responsaveis.insert(0, nota.autor)
        nota.responsavel = responsaveis[0] if responsaveis else None
        nota.save()
        form.save_m2m()
        nota.responsaveis.add(nota.autor)
        messages.success(request, 'Nota atualizada.')
    else:
        messages.error(request, 'Não foi possível editar a nota. Revise os campos.')
    return redirect_empresa(request, 'dashboard_home')


@login_required
@require_POST
def alternar_nota(request, pk):
    nota = _get_nota_visivel(request, pk)
    nota.concluida = not nota.concluida
    nota.save(update_fields=['concluida', 'atualizada_em'])
    return redirect_empresa(request, 'dashboard_home')


@login_required
@require_POST
def excluir_nota(request, pk):
    nota = _get_nota_visivel(request, pk)
    if nota.autor_id != request.user.pk and not request.user.is_superuser:
        messages.error(request, 'Apenas quem criou a nota pode excluí-la.')
        return redirect_empresa(request, 'dashboard_home')
    nota.delete()
    messages.success(request, 'Nota excluída.')
    return redirect_empresa(request, 'dashboard_home')
