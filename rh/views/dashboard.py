import calendar
from datetime import date, timedelta

from django.db.models import Case, IntegerField, Q, When
from django.shortcuts import redirect, render

from core.urlutils import reverse_empresa

from apontamento.models import (
    ApontamentoFalta,
    ApontamentoObservacaoLocal,
    StatusApontamento,
)
from controles_rh.models import Competencia

from ..perfil_secao import perfil_funcionario_url_por_tipo
from ..models import (
    AfastamentoFuncionario,
    ASOFuncionario,
    FeriasFuncionario,
    Funcionario,
    LembreteRH,
    PCMSOFuncionario,
)
from .base import _empresa_ativa_or_redirect


# ==========================================================
# CALENDÁRIO RH - MONTAGEM DOS EVENTOS
# ==========================================================
def _montar_eventos_calendario_rh(request, empresa_ativa, ano, mes):
    """
    Monta todos os eventos do calendário mensal do RH.

    Retorna:
    - nome do mês
    - nomes dos dias
    - semanas do calendário
    - eventos agrupados por dia

    Eventos considerados:
    - admissão
    - prorrogação de experiência
    - aviso
    - demissão
    - férias
    - afastamentos
    - ASO
    - vencimento de PCMSO
    - lembretes manuais
    - feriados fixos
    """
    funcionarios = Funcionario.objects.filter(
        empresa=empresa_ativa
    ).exclude(
        situacao_atual__in=['demitido', 'inativo']
    ).select_related(
        "cargo",
        "lotacao",
        "tipo_contrato",
    )

    eventos_por_dia = {}

    def add_evento(data_evento, tipo, label, funcionario=None, detalhe_url=None, extra=None):
        """
        Adiciona um evento no dicionário do calendário,
        desde que ele pertença ao mês/ano visualizado.
        """
        if not data_evento or data_evento.year != ano or data_evento.month != mes:
            return

        dia = data_evento.day

        if not detalhe_url and funcionario:
            detalhe_url = perfil_funcionario_url_por_tipo(
                request, funcionario.pk, tipo,
            )

        eventos_por_dia.setdefault(dia, []).append({
            "tipo": tipo,
            "label": label,
            "funcionario_nome": funcionario.nome if funcionario else "",
            "detalhe_url": detalhe_url,
            "extra": extra or "",
        })

    # --------------------------------------------------
    # EVENTOS DO FUNCIONÁRIO
    # --------------------------------------------------
    for func in funcionarios.order_by("nome"):
        if func.data_nascimento and func.data_nascimento.month == mes:
            try:
                data_aniversario = date(ano, mes, func.data_nascimento.day)
            except ValueError:
                # Ex.: 29/02 em ano não bissexto
                data_aniversario = date(ano, mes, 28)

            add_evento(
                data_aniversario,
                "aniversario",
                "Aniversário",
                func,
            )

        if func.data_admissao:
            add_evento(func.data_admissao, "admissao", "Admissão", func)

            data_45 = func.data_admissao + timedelta(days=45)
            if not func.inicio_prorrogacao:
                add_evento(
                    data_45,
                    "experiencia_45",
                    "45 dias / iniciar prorrogação",
                    func,
                )

        if func.inicio_prorrogacao:
            add_evento(
                func.inicio_prorrogacao,
                "inicio_prorrogacao",
                "Início da prorrogação",
                func,
            )

        if func.fim_prorrogacao:
            add_evento(
                func.fim_prorrogacao,
                "fim_prorrogacao",
                "Fim da prorrogação",
                func,
            )

        if func.data_inicio_aviso:
            add_evento(
                func.data_inicio_aviso,
                "inicio_aviso",
                "Início do aviso",
                func,
            )

        if func.data_fim_aviso:
            add_evento(
                func.data_fim_aviso,
                "fim_aviso",
                "Fim do aviso",
                func,
            )

        if func.data_demissao:
            add_evento(
                func.data_demissao,
                "demissao",
                "Demissão",
                func,
            )

        # Exame anual com base no ASO admissional,
        # ou na admissão caso não exista ASO admissional.
        aso_admissional = func.asos.filter(tipo="admissional").order_by("-data").first()
        data_base_exame = aso_admissional.data if aso_admissional else func.data_admissao

        if data_base_exame:
            try:
                renovacao = data_base_exame.replace(year=ano)
            except ValueError:
                renovacao = data_base_exame.replace(year=ano, day=28)

            alerta_renovacao = renovacao - timedelta(days=30)

            add_evento(
                renovacao,
                "renovacao_exame",
                "Renovar exame anual",
                func,
            )
            add_evento(
                alerta_renovacao,
                "alerta_exame",
                "Aviso: renovar exame em 30 dias",
                func,
            )

        if func.data_ultimo_exame:
            add_evento(
                func.data_ultimo_exame,
                "ultimo_exame",
                "Data do último exame",
                func,
            )

    # --------------------------------------------------
    # FÉRIAS
    # --------------------------------------------------
    ferias = FeriasFuncionario.objects.filter(
        funcionario__empresa=empresa_ativa
    ).select_related("funcionario")

    for item in ferias:
        if item.gozo_inicio:
            add_evento(
                item.gozo_inicio,
                "ferias_inicio",
                "Início de férias",
                item.funcionario,
            )
        if item.gozo_fim:
            add_evento(
                item.gozo_fim,
                "ferias_volta",
                "Volta de férias",
                item.funcionario,
            )

    # --------------------------------------------------
    # AFASTAMENTOS
    # --------------------------------------------------
    afastamentos = AfastamentoFuncionario.objects.filter(
        funcionario__empresa=empresa_ativa
    ).select_related("funcionario")

    for item in afastamentos:
        add_evento(
            item.data_afastamento,
            "afastamento",
            f"Afastamento - {item.get_tipo_display()}",
            item.funcionario,
        )

        if item.previsao_retorno:
            add_evento(
                item.previsao_retorno,
                "retorno_afastamento",
                "Previsão de retorno do afastamento",
                item.funcionario,
            )

    # --------------------------------------------------
    # ASO
    # --------------------------------------------------
    asos = ASOFuncionario.objects.filter(
        funcionario__empresa=empresa_ativa
    ).select_related("funcionario")

    for item in asos:
        add_evento(
            item.data,
            "aso",
            f"ASO - {item.get_tipo_display()}",
            item.funcionario,
        )

    # --------------------------------------------------
    # PCMSO
    # --------------------------------------------------
    pcmso_items = PCMSOFuncionario.objects.filter(
        funcionario__empresa=empresa_ativa
    ).select_related("funcionario")

    for item in pcmso_items:
        add_evento(
            item.data_vencimento,
            "pcmso",
            "Vencimento de PCMSO",
            item.funcionario,
        )

    # --------------------------------------------------
    # LEMBRETES MANUAIS
    # --------------------------------------------------
    lembretes = LembreteRH.objects.filter(
        empresa=empresa_ativa
    ).select_related("funcionario")

    for item in lembretes:
        detalhe = reverse_empresa(
            request,
            'rh:editar_lembrete_rh',
            kwargs={'pk': item.pk},
        )
        add_evento(
            item.data,
            "lembrete",
            item.titulo,
            item.funcionario,
            detalhe_url=detalhe,
            extra=item.descricao,
        )

    # --------------------------------------------------
    # FERIADOS FIXOS
    # --------------------------------------------------
    feriados_fixos = [
        (1, 1, "Confraternização Universal"),
        (4, 21, "Tiradentes"),
        (5, 1, "Dia do Trabalhador"),
        (9, 7, "Independência do Brasil"),
        (10, 12, "Nossa Senhora Aparecida"),
        (11, 2, "Finados"),
        (11, 15, "Proclamação da República"),
        (12, 25, "Natal"),
    ]

    for mes_f, dia_f, nome in feriados_fixos:
        if mes_f == mes:
            add_evento(
                date(ano, mes_f, dia_f),
                "feriado",
                nome,
                funcionario=None,
                detalhe_url=None,
            )

    # Ordena eventos do dia
    for dia in eventos_por_dia:
        eventos_por_dia[dia] = sorted(
            eventos_por_dia[dia],
            key=lambda e: (e["label"], e["funcionario_nome"]),
        )

    nomes_meses = {
        1: "Janeiro",
        2: "Fevereiro",
        3: "Março",
        4: "Abril",
        5: "Maio",
        6: "Junho",
        7: "Julho",
        8: "Agosto",
        9: "Setembro",
        10: "Outubro",
        11: "Novembro",
        12: "Dezembro",
    }

    nomes_dias = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]

    cal = calendar.Calendar(firstweekday=6)
    semanas_brutas = cal.monthdayscalendar(ano, mes)
    calendario_semanas = []

    hoje_real = date.today()

    for semana in semanas_brutas:
        linha = []
        for dia in semana:
            linha.append({
                "numero": dia,
                "eventos": eventos_por_dia.get(dia, []) if dia else [],
                "tem_evento": bool(eventos_por_dia.get(dia, [])) if dia else False,
                "is_today": dia == hoje_real.day and mes == hoje_real.month and ano == hoje_real.year,
            })
        calendario_semanas.append(linha)

    return {
        "mes_nome": nomes_meses[mes],
        "nomes_dias": nomes_dias,
        "calendario_semanas": calendario_semanas,
        "eventos_por_dia": eventos_por_dia,
    }


# ==========================================================
# PÁGINA DO CALENDÁRIO
# ==========================================================
def calendario_rh(request):
    """
    Exibe o calendário mensal do RH.

    Permite navegação por mês e ano via querystring:
    - ?mes=3&ano=2026
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa para visualizar o calendário do RH.",
    )
    if redirect_response:
        return redirect_response

    hoje = date.today()

    try:
        ano = int(request.GET.get("ano", hoje.year))
    except (TypeError, ValueError):
        ano = hoje.year

    try:
        mes = int(request.GET.get("mes", hoje.month))
    except (TypeError, ValueError):
        mes = hoje.month

    if mes < 1:
        mes = 12
        ano -= 1
    elif mes > 12:
        mes = 1
        ano += 1

    if mes == 1:
        mes_anterior, ano_anterior = 12, ano - 1
    else:
        mes_anterior, ano_anterior = mes - 1, ano

    if mes == 12:
        mes_proximo, ano_proximo = 1, ano + 1
    else:
        mes_proximo, ano_proximo = mes + 1, ano

    calendario_context = _montar_eventos_calendario_rh(request, empresa_ativa, ano, mes)

    lembretes = LembreteRH.objects.filter(
        empresa=empresa_ativa
    ).select_related("funcionario").order_by("data", "titulo")

    context = {
        "ano": ano,
        "mes": mes,
        "ano_anterior": ano_anterior,
        "mes_anterior": mes_anterior,
        "ano_proximo": ano_proximo,
        "mes_proximo": mes_proximo,
        "lembretes": lembretes,
        **calendario_context,
    }
    return render(request, "rh/calendario.html", context)


# ==========================================================
# DASHBOARD PRINCIPAL DO RH
# ==========================================================
_NOMES_MESES_RH = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


def _context_dashboard_funcionarios(request, empresa_ativa):
    """
    KPIs + lista de aniversariantes do mês (card esquerdo).
    """
    hoje = date.today()
    funcionarios_ativos = Funcionario.objects.filter(
        empresa=empresa_ativa,
    ).exclude(
        situacao_atual__in=['demitido', 'inativo'],
    ).select_related("cargo")

    total_funcionarios = funcionarios_ativos.count()

    total_ferias = FeriasFuncionario.objects.filter(
        funcionario__empresa=empresa_ativa,
        gozo_inicio__isnull=False,
        gozo_fim__isnull=False,
        gozo_inicio__lte=hoje,
        gozo_fim__gte=hoje,
    ).values("funcionario_id").distinct().count()

    total_experiencia = funcionarios_ativos.filter(
        data_admissao__isnull=False,
        data_admissao__lte=hoje,
        fim_prorrogacao__isnull=False,
        fim_prorrogacao__gte=hoje,
    ).count()

    total_aviso = funcionarios_ativos.filter(
        data_inicio_aviso__isnull=False,
        data_fim_aviso__isnull=False,
        data_inicio_aviso__lte=hoje,
        data_fim_aviso__gte=hoje,
    ).count()

    aniversariantes_mes = []
    for func in funcionarios_ativos.filter(data_nascimento__isnull=False):
        if func.data_nascimento.month == hoje.month:
            aniversariantes_mes.append(
                {
                    "nome": func.nome,
                    "cargo": func.cargo.nome if func.cargo else "",
                    "dia": func.data_nascimento.day,
                    "detalhe_url": perfil_funcionario_url_por_tipo(
                        request, func.pk, "aniversario",
                    ),
                }
            )

    aniversariantes_mes.sort(key=lambda item: (item["dia"], item["nome"]))

    return {
        "mes_nome": _NOMES_MESES_RH[hoje.month],
        "total_funcionarios": total_funcionarios,
        "total_ferias": total_ferias,
        "total_experiencia": total_experiencia,
        "total_aviso": total_aviso,
        "aniversariantes_mes": aniversariantes_mes,
    }


def _context_dashboard_avisos(request, empresa_ativa):
    """
    Destaques do dia e da semana no card AVISOS (janela: domingo a sábado da semana corrente).

    Não monta eventos do mês inteiro — isso fica pesado e duplica o calendário completo,
    que continua disponível apenas em «Ver calendário» (calendario_rh).
    """
    hoje = date.today()
    inicio_semana = hoje - timedelta(days=(hoje.weekday() + 1) % 7)
    fim_semana = inicio_semana + timedelta(days=6)

    funcionarios_ativos = Funcionario.objects.filter(
        empresa=empresa_ativa,
    ).exclude(
        situacao_atual__in=['demitido', 'inativo'],
    ).select_related(
        "cargo",
        "lotacao",
        "tipo_contrato",
    ).prefetch_related("asos")

    eventos_por_data = {}

    def add_evento(data_evento, tipo, label, funcionario=None):
        if not data_evento or data_evento < inicio_semana or data_evento > fim_semana:
            return

        detalhe_url = None
        if funcionario:
            detalhe_url = perfil_funcionario_url_por_tipo(
                request, funcionario.pk, tipo,
            )

        eventos_por_data.setdefault(data_evento, []).append({
            "tipo": tipo,
            "label": label,
            "funcionario_nome": funcionario.nome if funcionario else "",
            "detalhe_url": detalhe_url,
        })

    ferias_janela = FeriasFuncionario.objects.filter(
        funcionario__empresa=empresa_ativa,
    ).filter(
        Q(gozo_inicio__gte=inicio_semana, gozo_inicio__lte=fim_semana) |
        Q(gozo_fim__gte=inicio_semana, gozo_fim__lte=fim_semana),
    ).select_related("funcionario", "funcionario__cargo")

    for item in ferias_janela:
        if item.gozo_inicio:
            add_evento(item.gozo_inicio, "ferias_inicio", "Início de férias", item.funcionario)
        if item.gozo_fim:
            add_evento(item.gozo_fim, "ferias_volta", "Volta de férias", item.funcionario)

    for func in funcionarios_ativos.filter(
        data_admissao__isnull=False,
        inicio_prorrogacao__isnull=True,
        data_admissao__gte=inicio_semana - timedelta(days=45),
        data_admissao__lte=fim_semana - timedelta(days=45),
    ):
        data_45 = func.data_admissao + timedelta(days=45)
        if inicio_semana <= data_45 <= fim_semana:
            add_evento(data_45, "experiencia_45", "45 dias / iniciar prorrogação", func)

    for func in funcionarios_ativos.filter(
        fim_prorrogacao__gte=inicio_semana,
        fim_prorrogacao__lte=fim_semana,
    ):
        add_evento(func.fim_prorrogacao, "fim_prorrogacao", "Fim da prorrogação", func)

    for func in funcionarios_ativos.filter(
        data_fim_aviso__gte=inicio_semana,
        data_fim_aviso__lte=fim_semana,
    ):
        add_evento(func.data_fim_aviso, "fim_aviso", "Fim de aviso", func)

    for func in funcionarios_ativos.filter(data_admissao__isnull=False).order_by("nome"):
        aso_admissional = func.asos.filter(tipo="admissional").order_by("-data").first()
        data_base = aso_admissional.data if aso_admissional else func.data_admissao

        if not data_base:
            continue

        try:
            proximo_exame = data_base.replace(year=hoje.year)
        except ValueError:
            proximo_exame = data_base.replace(year=hoje.year, day=28)

        if proximo_exame < hoje:
            try:
                proximo_exame = proximo_exame.replace(year=hoje.year + 1)
            except ValueError:
                proximo_exame = proximo_exame.replace(year=hoje.year + 1, day=28)

        if (
            0 <= (proximo_exame - hoje).days <= 30
            and inicio_semana <= proximo_exame <= fim_semana
        ):
            add_evento(proximo_exame, "exame", "Exame periódico", func)

    lembretes_janela = LembreteRH.objects.filter(
        empresa=empresa_ativa,
        data__gte=inicio_semana,
        data__lte=fim_semana,
    ).select_related("funcionario").order_by("data", "titulo")

    for item in lembretes_janela:
        add_evento(item.data, "lembrete", item.titulo, item.funcionario)

    dias_semana = [inicio_semana + timedelta(days=i) for i in range(7)]
    q_aniv = Q()
    for d in dias_semana:
        q_aniv |= Q(data_nascimento__month=d.month, data_nascimento__day=d.day)

    for func in funcionarios_ativos.filter(
        data_nascimento__isnull=False,
    ).filter(q_aniv).order_by("nome"):
        for d in dias_semana:
            if (
                func.data_nascimento.month == d.month
                and func.data_nascimento.day == d.day
            ):
                add_evento(d, "aniversario", "Aniversário", func)

    for d_key in eventos_por_data:
        eventos_por_data[d_key] = sorted(
            eventos_por_data[d_key],
            key=lambda e: (e["label"], e["funcionario_nome"]),
        )

    destaques_dia = [
        {"data": hoje, **evento}
        for evento in eventos_por_data.get(hoje, [])
    ]

    destaques_semana = []
    for d in sorted(eventos_por_data.keys()):
        for evento in eventos_por_data[d]:
            destaques_semana.append({"data": d, **evento})

    destaques_semana.sort(
        key=lambda e: (e["data"], e["label"], e["funcionario_nome"])
    )

    return {
        "destaques_dia": destaques_dia,
        "destaques_semana": destaques_semana,
    }


def dashboard_partial_gestao_rh(request):
    """
    Card hero «Gestão de RH» (competências, VT, cesta, faltas…).
    Carregado via HTMX com skeleton no shell.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa para visualizar o RH.",
    )
    if redirect_response:
        return redirect_response

    ultima_competencia = (
        Competencia.objects.filter(empresa=empresa_ativa)
        .order_by("-ano", "-mes")
        .first()
    )

    return render(
        request,
        "rh/partials/dashboard_gestao_rh_hero.html",
        {"ultima_competencia": ultima_competencia},
    )


def _usuario_pode_alterar_status_apontamento(request):
    return bool(
        request.user.is_superuser
        or getattr(request, "usuario_admin_empresa", False)
    )


def _ordem_status_apontamento():
    return Case(
        When(status=StatusApontamento.PENDENTE, then=0),
        When(status=StatusApontamento.FINALIZADO, then=1),
        When(status=StatusApontamento.ARQUIVADO, then=2),
        default=0,
        output_field=IntegerField(),
    )


def _contexto_card_apontamento(empresa_ativa):
    ord_case = _ordem_status_apontamento()
    apont_faltas = (
        ApontamentoFalta.objects.filter(empresa=empresa_ativa)
        .select_related("funcionario", "registrado_por")
        .annotate(_st_ord=ord_case)
        .order_by("_st_ord", "-criado_em")[:15]
    )
    apont_observacoes = (
        ApontamentoObservacaoLocal.objects.filter(empresa=empresa_ativa)
        .select_related("local", "registrado_por")
        .annotate(_st_ord=ord_case)
        .order_by("_st_ord", "-criado_em")[:15]
    )
    return {
        "apont_faltas": apont_faltas,
        "apont_observacoes": apont_observacoes,
    }


def render_dashboard_apontamento_partial(request):
    """
    HTML do card «Apontamento» (dashboard RH): uso em HTMX e após alterar status.
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa para visualizar o RH.",
    )
    if redirect_response:
        return redirect_response

    ctx = _contexto_card_apontamento(empresa_ativa)
    ctx["pode_alterar_status_apontamento"] = _usuario_pode_alterar_status_apontamento(
        request
    )
    ctx["status_apontamento_choices"] = StatusApontamento.choices
    return render(request, "rh/partials/dashboard_apontamento_body.html", ctx)


def dashboard_partial_apontamento(request):
    """
    Card «Apontamento»: faltas e observações registradas em campo (não oficiais).
    """
    return render_dashboard_apontamento_partial(request)


def dashboard_rh(request):
    """
    Shell do dashboard: conteúdo dos cards carrega em paralelo via HTMX (partials).
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa para visualizar o RH.",
    )
    if redirect_response:
        return redirect_response

    return render(request, "rh/dashboard.html", {})


def dashboard_partial_funcionarios(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa para visualizar o RH.",
    )
    if redirect_response:
        return redirect_response

    context = _context_dashboard_funcionarios(request, empresa_ativa)
    return render(request, "rh/partials/dashboard_funcionarios_body.html", context)


def dashboard_partial_avisos(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa para visualizar o RH.",
    )
    if redirect_response:
        return redirect_response

    context = _context_dashboard_avisos(request, empresa_ativa)
    return render(request, "rh/partials/dashboard_avisos_oob.html", context)