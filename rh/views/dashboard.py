import calendar
from datetime import date, timedelta

from django.db.models import Q
from django.shortcuts import render

from core.urlutils import reverse_empresa

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
            detalhe_url = reverse_empresa(
                request,
                'rh:detalhes_funcionario',
                kwargs={'pk': funcionario.pk},
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
def dashboard_rh(request):
    """
    Dashboard principal do RH com:
    - totais principais
    - calendário resumido do mês
    - férias ativas
    - funcionários em experiência
    - funcionários em aviso
    - exames próximos
    """
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa para visualizar o RH.",
    )
    if redirect_response:
        return redirect_response

    hoje = date.today()
    ano = hoje.year
    mes = hoje.month
    limite_experiencia = hoje - timedelta(days=45)

    funcionarios = Funcionario.objects.filter(
        empresa=empresa_ativa
    ).select_related(
        "cargo",
        "lotacao",
        "tipo_contrato",
    )

    total_funcionarios = funcionarios.count()

    funcionarios_ativos = funcionarios.exclude(
        situacao_atual__in=['demitido', 'inativo']
    )

    # --------------------------------------------------
    # FUNCIONÁRIOS EM FÉRIAS NO MOMENTO
    # --------------------------------------------------
    ferias_ativas_qs = FeriasFuncionario.objects.filter(
        funcionario__empresa=empresa_ativa,
        gozo_inicio__isnull=False,
        gozo_fim__isnull=False,
        gozo_inicio__lte=hoje,
        gozo_fim__gte=hoje,
    ).select_related("funcionario").order_by("gozo_fim")

    total_ferias = ferias_ativas_qs.values("funcionario_id").distinct().count()

    # --------------------------------------------------
    # FUNCIONÁRIOS EM EXPERIÊNCIA
    # --------------------------------------------------
    experiencia_qs = funcionarios_ativos.filter(
        Q(
            data_admissao__isnull=False,
            data_admissao__gte=limite_experiencia,
            inicio_prorrogacao__isnull=True,
        ) |
        Q(
            inicio_prorrogacao__isnull=False,
            fim_prorrogacao__isnull=False,
            inicio_prorrogacao__lte=hoje,
            fim_prorrogacao__gte=hoje,
        )
    ).order_by("nome")

    total_experiencia = experiencia_qs.count()

    # --------------------------------------------------
    # FUNCIONÁRIOS EM AVISO
    # --------------------------------------------------
    aviso_qs = funcionarios_ativos.filter(
        data_inicio_aviso__isnull=False,
        data_fim_aviso__isnull=False,
        data_inicio_aviso__lte=hoje,
        data_fim_aviso__gte=hoje,
    ).order_by("data_fim_aviso", "nome")

    total_aviso = aviso_qs.count()

    # --------------------------------------------------
    # CALENDÁRIO RESUMIDO DO DASHBOARD
    # --------------------------------------------------
    eventos_por_dia = {}

    def add_evento(data_evento, tipo, label, funcionario=None):
        """
        Adiciona evento no calendário resumido do dashboard.
        """
        if not data_evento or data_evento.year != ano or data_evento.month != mes:
            return

        dia = data_evento.day
        detalhe_url = None

        if funcionario:
            detalhe_url = reverse_empresa(
                request,
                'rh:detalhes_funcionario',
                kwargs={'pk': funcionario.pk},
            )

        eventos_por_dia.setdefault(dia, []).append({
            "tipo": tipo,
            "label": label,
            "funcionario_nome": funcionario.nome if funcionario else "",
            "detalhe_url": detalhe_url,
        })

    # Férias do mês
    ferias_mes = FeriasFuncionario.objects.filter(
        funcionario__empresa=empresa_ativa
    ).select_related("funcionario", "funcionario__cargo")

    for item in ferias_mes:
        if item.gozo_inicio:
            add_evento(item.gozo_inicio, "ferias_inicio", "Início de férias", item.funcionario)
        if item.gozo_fim:
            add_evento(item.gozo_fim, "ferias_volta", "Volta de férias", item.funcionario)

    # Alertas de experiência
    experiencia_alertas = funcionarios_ativos.filter(
        data_admissao__isnull=False
    ).order_by("data_admissao")

    for func in experiencia_alertas:
        data_45 = func.data_admissao + timedelta(days=45)

        if data_45.month == mes and data_45.year == ano and not func.inicio_prorrogacao:
            add_evento(data_45, "experiencia_45", "45 dias / iniciar prorrogação", func)

        if func.fim_prorrogacao:
            add_evento(func.fim_prorrogacao, "fim_prorrogacao", "Fim da prorrogação", func)

    # Fim do aviso
    aviso_mes = funcionarios_ativos.filter(
        data_fim_aviso__isnull=False
    ).order_by("data_fim_aviso")

    for func in aviso_mes:
        add_evento(func.data_fim_aviso, "fim_aviso", "Fim de aviso", func)

    # Exames próximos
    exames_proximos = []
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

        if 0 <= (proximo_exame - hoje).days <= 30:
            exames_proximos.append({
                "funcionario": func,
                "data": proximo_exame,
            })
            add_evento(proximo_exame, "exame", "Exame periódico", func)

    exames_proximos = sorted(exames_proximos, key=lambda x: x["data"])[:20]

    # Lembretes manuais
    lembretes_dashboard = LembreteRH.objects.filter(
        empresa=empresa_ativa,
    ).select_related("funcionario").order_by("data", "titulo")

    for item in lembretes_dashboard:
        add_evento(item.data, "lembrete", item.titulo, item.funcionario)

    # Ordenação dos eventos por dia
    for dia in eventos_por_dia:
        eventos_por_dia[dia] = sorted(
            eventos_por_dia[dia],
            key=lambda e: (e["label"], e["funcionario_nome"]),
        )

    # Destaques listados para leitura rápida na dashboard
    destaques_dia = []
    for evento in eventos_por_dia.get(hoje.day, []):
        destaques_dia.append(
            {
                "data": hoje,
                **evento,
            }
        )

    inicio_semana = hoje - timedelta(days=(hoje.weekday() + 1) % 7)  # domingo
    fim_semana = inicio_semana + timedelta(days=6)
    destaques_semana = []

    for dia_numero, eventos in eventos_por_dia.items():
        data_evento = date(ano, mes, dia_numero)
        if inicio_semana <= data_evento <= fim_semana:
            for evento in eventos:
                destaques_semana.append(
                    {
                        "data": data_evento,
                        **evento,
                    }
                )

    destaques_semana.sort(
        key=lambda e: (e["data"], e["label"], e["funcionario_nome"])
    )

    aniversariantes_mes = []
    for func in funcionarios_ativos.filter(data_nascimento__isnull=False):
        if func.data_nascimento.month == hoje.month:
            aniversariantes_mes.append(
                {
                    "nome": func.nome,
                    "cargo": func.cargo.nome if func.cargo else "",
                    "dia": func.data_nascimento.day,
                    "detalhe_url": reverse_empresa(
                        request,
                        'rh:detalhes_funcionario',
                        kwargs={'pk': func.pk},
                    ),
                }
            )

    aniversariantes_mes.sort(key=lambda item: (item["dia"], item["nome"]))

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

    for semana in semanas_brutas:
        linha = []
        for dia in semana:
            linha.append({
                "numero": dia,
                "eventos": eventos_por_dia.get(dia, []) if dia else [],
                "tem_evento": bool(eventos_por_dia.get(dia, [])) if dia else False,
                "is_today": dia == hoje.day,
            })
        calendario_semanas.append(linha)

    context = {
        "hoje": hoje,
        "mes_nome": nomes_meses[mes],
        "ano": ano,
        "nomes_dias": nomes_dias,

        "total_funcionarios": total_funcionarios,
        "total_ferias": total_ferias,
        "total_experiencia": total_experiencia,
        "total_aviso": total_aviso,

        "calendario_semanas": calendario_semanas,
        "eventos_por_dia": eventos_por_dia,
        "destaques_dia": destaques_dia,
        "destaques_semana": destaques_semana,
        "aniversariantes_mes": aniversariantes_mes,

        "exames_proximos": exames_proximos[:8],
        "ferias_ativas": ferias_ativas_qs[:8],
        "experiencia_lista": experiencia_qs[:8],
        "aviso_lista": aviso_qs[:8],
    }
    return render(request, "rh/dashboard.html", context)