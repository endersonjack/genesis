from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from empresas.models import Empresa

from auditoria.models import RegistroAuditoria
from usuarios.models import UsuarioEmpresa

# Valores gravados em `modulo` via registrar_auditoria + filtros de agrupamento
MODULO_FILTRO_CHOICES = [
    ('', 'Todos'),
    ('rh', 'RH'),
    ('financeiro', 'Financeiro'),
    ('estoque', 'Estoque'),
    ('empresas', 'Empresa'),
    ('controles_rh', 'Controles RH'),
    ('local', 'Locais'),
    ('outros', 'Outros'),
]


def _q_modulo(modulo_val: str) -> Q:
    if not modulo_val:
        return Q()
    if modulo_val == 'rh':
        return Q(modulo__in=['rh', 'controles_rh'])
    if modulo_val == 'outros':
        conhecidos = {'rh', 'controles_rh', 'financeiro', 'estoque', 'empresas', 'local'}
        return Q(modulo='') | ~Q(modulo__in=conhecidos)
    return Q(modulo=modulo_val)


PER_PAGE_PADRAO = 20
PER_PAGE_OPCOES = (20, 50, 100)


def _querystring_sem_page(request) -> str:
    q = request.GET.copy()
    q.pop('page', None)
    return q.urlencode()


def _resolver_por_pagina(request) -> int:
    raw = request.GET.get('por_pagina') or ''
    try:
        n = int(raw)
    except ValueError:
        return PER_PAGE_PADRAO
    if n not in PER_PAGE_OPCOES:
        return PER_PAGE_PADRAO
    return n


def _querystrings_por_pagina(request) -> dict[int, str]:
    """Query string para trocar itens/página (remove page → volta à página 1)."""
    out = {}
    for n in PER_PAGE_OPCOES:
        q = request.GET.copy()
        q.pop('page', None)
        q['por_pagina'] = str(n)
        out[n] = q.urlencode()
    return out


@login_required
def lista_auditoria(request):
    pode_ver_todos = bool(
        getattr(request, 'usuario_admin_empresa', False) or request.user.is_superuser
    )
    if not pode_ver_todos:
        raise PermissionDenied()

    qs = RegistroAuditoria.objects.filter(empresa=request.empresa_ativa).select_related(
        'usuario',
    )

    usuario_id = request.GET.get('usuario') or ''
    modulo_filtro = request.GET.get('modulo') or ''
    acao_filtro = request.GET.get('acao') or ''

    valid_modulos = {c[0] for c in MODULO_FILTRO_CHOICES}
    if modulo_filtro not in valid_modulos:
        modulo_filtro = ''

    valid_acoes = {c[0] for c in RegistroAuditoria.ACAO_CHOICES}
    if acao_filtro not in valid_acoes:
        acao_filtro = ''

    if pode_ver_todos and usuario_id.isdigit():
        qs = qs.filter(usuario_id=int(usuario_id))

    qs = qs.filter(_q_modulo(modulo_filtro))

    if acao_filtro:
        qs = qs.filter(acao=acao_filtro)

    por_pagina = _resolver_por_pagina(request)
    paginator = Paginator(qs, por_pagina)
    page = paginator.get_page(request.GET.get('page') or 1)

    User = get_user_model()
    usuarios_empresa = []
    if pode_ver_todos:
        uids = (
            UsuarioEmpresa.objects.filter(
                empresa=request.empresa_ativa,
                ativo=True,
            )
            .values_list('usuario_id', flat=True)
            .distinct()
        )
        usuarios_empresa = (
            User.objects.filter(pk__in=uids)
            .order_by('nome_completo', 'username')
        )

    filtros_ativos = bool(usuario_id or modulo_filtro or acao_filtro)

    empresas_acesso = list(
        Empresa.objects.filter(
            pk__in=UsuarioEmpresa.objects.filter(
                usuario=request.user,
                ativo=True,
                empresa__ativa=True,
            ).values_list('empresa_id', flat=True),
        ).order_by('razao_social', 'nome_fantasia')
    )

    qs_tamanho_pagina = _querystrings_por_pagina(request)
    botoes_por_pagina = [(n, qs_tamanho_pagina[n]) for n in PER_PAGE_OPCOES]

    return render(
        request,
        'auditoria/lista.html',
        {
            'page_obj': page,
            'pode_ver_todos': pode_ver_todos,
            'modulo_filtro_choices': MODULO_FILTRO_CHOICES,
            'acao_filtro_choices': RegistroAuditoria.ACAO_CHOICES,
            'usuarios_empresa': usuarios_empresa,
            'filtro_usuario': usuario_id,
            'filtro_modulo': modulo_filtro,
            'filtro_acao': acao_filtro,
            'filtros_ativos': filtros_ativos,
            'filter_query': _querystring_sem_page(request),
            'empresas_acesso': empresas_acesso,
            'mostrar_seletor_empresa': len(empresas_acesso) > 1,
            'per_page': por_pagina,
            'botoes_por_pagina': botoes_por_pagina,
        },
    )
