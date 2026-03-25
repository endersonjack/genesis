from datetime import date, timedelta, datetime
from django.urls import reverse
import calendar
import json
from django.contrib import messages
from django.db import transaction
from datetime import timedelta
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from .forms import *
from .models import *
from rh.utils.historico import registrar_alteracao_situacao
from django.http import HttpResponse


def _empresa_ativa_or_redirect(request, mensagem='Selecione uma empresa para continuar.'):
    empresa_ativa = getattr(request, 'empresa_ativa', None)
    if not empresa_ativa:
        messages.warning(request, mensagem)
        return None, redirect('selecionar_empresa')
    return empresa_ativa, None


def _montar_formsets_funcionario(request=None, instance=None):
    """
    Centraliza a criação dos formsets para create/edit.
    """
    is_post = request is not None and request.method == 'POST'
    post_data = request.POST if is_post else None
    file_data = request.FILES if is_post else None

    return {
        'dependente_formset': DependenteFormSet(
            post_data,
            file_data,
            instance=instance,
            prefix='dependentes',
        ),
        'ferias_formset': FeriasFuncionarioFormSet(
            post_data,
            file_data,
            instance=instance,
            prefix='ferias',
        ),
        'afastamento_formset': AfastamentoFuncionarioFormSet(
            post_data,
            file_data,
            instance=instance,
            prefix='afastamentos',
        ),
        'aso_formset': ASOFuncionarioFormSet(
            post_data,
            file_data,
            instance=instance,
            prefix='asos',
        ),
        'certificado_formset': CertificadoFuncionarioFormSet(
            post_data,
            file_data,
            instance=instance,
            prefix='certificados',
        ),
        'pcmso_formset': PCMSOFuncionarioFormSet(
            post_data,
            file_data,
            instance=instance,
            prefix='pcmso',
        ),
        'atestado_licenca_formset': AtestadoLicencaFuncionarioFormSet(
            post_data,
            file_data,
            instance=instance,
            prefix='atestados_licencas',
        ),
        'ocorrencia_saude_formset': OcorrenciaSaudeFuncionarioFormSet(
            post_data,
            file_data,
            instance=instance,
            prefix='ocorrencias_saude',
        ),
    }


def _todos_formsets_validos(formsets_dict):
    return all(formset.is_valid() for formset in formsets_dict.values())


def _salvar_todos_formsets(funcionario, formsets_dict):
    for formset in formsets_dict.values():
        formset.instance = funcionario
        formset.save()

####################### CRIAR FUNCIONÁRIO MODO RÁPIDO  #################################

@transaction.atomic
def modal_novo_funcionario_rapido(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de cadastrar funcionários.'
    )
    if redirect_response:
        return redirect_response

    if request.method == 'POST':
        form = FuncionarioCadastroRapidoForm(
            request.POST,
            empresa_ativa=empresa_ativa
        )

        if form.is_valid():
            funcionario = form.save(commit=False)
            funcionario.empresa = empresa_ativa
            funcionario.save()

            response = HttpResponse(status=204)
            response['HX-Redirect'] = reverse('rh:detalhes_funcionario', args=[funcionario.pk])
            return response
    else:
        form = FuncionarioCadastroRapidoForm(empresa_ativa=empresa_ativa)

    return render(request, 'rh/funcionarios/modal_novo_rapido.html', {
        'form': form,
    })



####################### BUSCAR FUNCIONÁRIOS  #################################


def buscar_funcionarios(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para buscar funcionários.'
    )
    if redirect_response:
        return redirect_response

    hoje = date.today()

    funcionarios = Funcionario.objects.filter(
        empresa=empresa_ativa
    ).select_related(
        'empresa',
        'cargo',
        'lotacao',
        'tipo_contrato',
    ).prefetch_related('ferias', 'afastamentos')

    q = request.GET.get('q', '').strip()
    cargo_id = request.GET.get('cargo', '').strip()
    lotacao_id = request.GET.get('lotacao', '').strip()
    situacao = request.GET.get('situacao', '').strip()
    tipo_contrato_id = request.GET.get('tipo_contrato', '').strip()

    admissao_de = request.GET.get('admissao_de', '').strip()
    admissao_ate = request.GET.get('admissao_ate', '').strip()
    demissao_de = request.GET.get('demissao_de', '').strip()
    demissao_ate = request.GET.get('demissao_ate', '').strip()

    aviso_ativo = request.GET.get('aviso_ativo', '').strip()
    em_ferias = request.GET.get('em_ferias', '').strip()
    afastado = request.GET.get('afastado', '').strip()
    sem_cargo = request.GET.get('sem_cargo', '').strip()
    sem_lotacao = request.GET.get('sem_lotacao', '').strip()

    if q:
        funcionarios = funcionarios.filter(
            Q(nome__icontains=q) |
            Q(cpf__icontains=q) |
            Q(pis__icontains=q) |
            Q(matricula__icontains=q) |
            Q(rg__icontains=q)
        )

    if cargo_id:
        funcionarios = funcionarios.filter(cargo_id=cargo_id)

    if lotacao_id:
        funcionarios = funcionarios.filter(lotacao_id=lotacao_id)

    if situacao and situacao != 'todos':
        funcionarios = funcionarios.filter(situacao_atual=situacao)

    if tipo_contrato_id:
        funcionarios = funcionarios.filter(tipo_contrato_id=tipo_contrato_id)

    if admissao_de:
        funcionarios = funcionarios.filter(data_admissao__gte=admissao_de)

    if admissao_ate:
        funcionarios = funcionarios.filter(data_admissao__lte=admissao_ate)

    if demissao_de:
        funcionarios = funcionarios.filter(data_demissao__gte=demissao_de)

    if demissao_ate:
        funcionarios = funcionarios.filter(data_demissao__lte=demissao_ate)

    if aviso_ativo == '1':
        funcionarios = funcionarios.filter(
            data_inicio_aviso__isnull=False,
            data_fim_aviso__isnull=False,
            data_inicio_aviso__lte=hoje,
            data_fim_aviso__gte=hoje,
        )

    if em_ferias == '1':
        funcionarios = funcionarios.filter(
            ferias__gozo_inicio__lte=hoje,
            ferias__gozo_fim__gte=hoje,
        ).distinct()

    if afastado == '1':
        funcionarios = funcionarios.filter(situacao_atual='afastado')

    if sem_cargo == '1':
        funcionarios = funcionarios.filter(cargo__isnull=True)

    if sem_lotacao == '1':
        funcionarios = funcionarios.filter(lotacao__isnull=True)

    funcionarios = funcionarios.order_by('nome').distinct()

    cargos = Cargo.objects.filter(empresa=empresa_ativa).order_by('nome')
    lotacoes = Lotacao.objects.filter(empresa=empresa_ativa).order_by('nome')
    tipos_contrato = TipoContrato.objects.filter(empresa=empresa_ativa).order_by('nome')

    context = {
        'funcionarios': funcionarios,
        'cargos': cargos,
        'lotacoes': lotacoes,
        'tipos_contrato': tipos_contrato,
        'status_choices': Funcionario.STATUS_CHOICES,
        'total_resultados': funcionarios.count(),
        'filtros_ativos': any([
            q, cargo_id, lotacao_id, situacao, tipo_contrato_id,
            admissao_de, admissao_ate, demissao_de, demissao_ate,
            aviso_ativo, em_ferias, afastado, sem_cargo, sem_lotacao
        ]),
    }
    return render(request, 'rh/funcionarios/buscar.html', context)


####################### CALENDÁRIO RH #################################

def _montar_eventos_calendario_rh(empresa_ativa, ano, mes):
    funcionarios = Funcionario.objects.filter(
        empresa=empresa_ativa
    ).select_related('cargo', 'lotacao', 'tipo_contrato')

    eventos_por_dia = {}

    def add_evento(data_evento, tipo, label, funcionario=None, detalhe_url=None, extra=None):
        if not data_evento or data_evento.year != ano or data_evento.month != mes:
            return

        dia = data_evento.day

        if not detalhe_url and funcionario:
            detalhe_url = reverse('rh:detalhes_funcionario', args=[funcionario.pk])

        eventos_por_dia.setdefault(dia, []).append({
            'tipo': tipo,
            'label': label,
            'funcionario_nome': funcionario.nome if funcionario else '',
            'detalhe_url': detalhe_url,
            'extra': extra or '',
        })

    # -------------------------
    # FUNCIONÁRIO / ADMISSÃO / DEMISSÃO / AVISO / PRORROGAÇÃO
    # -------------------------
    for func in funcionarios.order_by('nome'):
        if func.data_admissao:
            add_evento(func.data_admissao, 'admissao', 'Admissão', func)

            data_45 = func.data_admissao + timedelta(days=45)
            if not func.inicio_prorrogacao:
                add_evento(data_45, 'experiencia_45', '45 dias / iniciar prorrogação', func)

        if func.inicio_prorrogacao:
            add_evento(func.inicio_prorrogacao, 'inicio_prorrogacao', 'Início da prorrogação', func)

        if func.fim_prorrogacao:
            add_evento(func.fim_prorrogacao, 'fim_prorrogacao', 'Fim da prorrogação', func)

        if func.data_inicio_aviso:
            add_evento(func.data_inicio_aviso, 'inicio_aviso', 'Início do aviso', func)

        if func.data_fim_aviso:
            add_evento(func.data_fim_aviso, 'fim_aviso', 'Fim do aviso', func)

        if func.data_demissao:
            add_evento(func.data_demissao, 'demissao', 'Demissão', func)

        # exame anual com base no ASO admissional
        aso_admissional = func.asos.filter(tipo='admissional').order_by('-data').first()
        data_base_exame = aso_admissional.data if aso_admissional else func.data_admissao

        if data_base_exame:
            try:
                renovacao = data_base_exame.replace(year=ano)
            except ValueError:
                renovacao = data_base_exame.replace(year=ano, day=28)

            alerta_renovacao = renovacao - timedelta(days=30)

            add_evento(renovacao, 'renovacao_exame', 'Renovar exame anual', func)
            add_evento(alerta_renovacao, 'alerta_exame', 'Aviso: renovar exame em 30 dias', func)

        if func.data_ultimo_exame:
            add_evento(func.data_ultimo_exame, 'ultimo_exame', 'Data do último exame', func)

    # -------------------------
    # FÉRIAS
    # -------------------------
    ferias = FeriasFuncionario.objects.filter(
        funcionario__empresa=empresa_ativa
    ).select_related('funcionario')

    for item in ferias:
        if item.gozo_inicio:
            add_evento(item.gozo_inicio, 'ferias_inicio', 'Início de férias', item.funcionario)
        if item.gozo_fim:
            add_evento(item.gozo_fim, 'ferias_volta', 'Volta de férias', item.funcionario)

    # -------------------------
    # AFASTAMENTOS
    # -------------------------
    afastamentos = AfastamentoFuncionario.objects.filter(
        funcionario__empresa=empresa_ativa
    ).select_related('funcionario')

    for item in afastamentos:
        add_evento(
            item.data_afastamento,
            'afastamento',
            f'Afastamento - {item.get_tipo_display()}',
            item.funcionario
        )
        if item.previsao_retorno:
            add_evento(
                item.previsao_retorno,
                'retorno_afastamento',
                'Previsão de retorno do afastamento',
                item.funcionario
            )

    # -------------------------
    # ASO
    # -------------------------
    asos = ASOFuncionario.objects.filter(
        funcionario__empresa=empresa_ativa
    ).select_related('funcionario')

    for item in asos:
        add_evento(
            item.data,
            'aso',
            f'ASO - {item.get_tipo_display()}',
            item.funcionario
        )

    # -------------------------
    # PCMSO
    # -------------------------
    pcmso_items = PCMSOFuncionario.objects.filter(
        funcionario__empresa=empresa_ativa
    ).select_related('funcionario')

    for item in pcmso_items:
        add_evento(
            item.data_vencimento,
            'pcmso',
            'Vencimento de PCMSO',
            item.funcionario
        )

    # -------------------------
    # LEMBRETES MANUAIS
    # -------------------------
    lembretes = LembreteRH.objects.filter(
        empresa=empresa_ativa
    ).select_related('funcionario')

    for item in lembretes:
        detalhe = reverse('rh:editar_lembrete_rh', args=[item.pk])
        add_evento(
            item.data,
            'lembrete',
            item.titulo,
            item.funcionario,
            detalhe_url=detalhe,
            extra=item.descricao
        )

    # -------------------------
    # FERIADOS FIXOS BÁSICOS
    # -------------------------
    feriados_fixos = [
        (1, 1, 'Confraternização Universal'),
        (4, 21, 'Tiradentes'),
        (5, 1, 'Dia do Trabalhador'),
        (9, 7, 'Independência do Brasil'),
        (10, 12, 'Nossa Senhora Aparecida'),
        (11, 2, 'Finados'),
        (11, 15, 'Proclamação da República'),
        (12, 25, 'Natal'),
    ]

    for mes_f, dia_f, nome in feriados_fixos:
        if mes_f == mes:
            add_evento(
                date(ano, mes_f, dia_f),
                'feriado',
                nome,
                funcionario=None,
                detalhe_url=None
            )

    for dia in eventos_por_dia:
        eventos_por_dia[dia] = sorted(
            eventos_por_dia[dia],
            key=lambda e: (e['label'], e['funcionario_nome'])
        )

    nomes_meses = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    nomes_dias = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']

    cal = calendar.Calendar(firstweekday=6)
    semanas_brutas = cal.monthdayscalendar(ano, mes)
    calendario_semanas = []

    hoje_real = date.today()

    for semana in semanas_brutas:
        linha = []
        for dia in semana:
            linha.append({
                'numero': dia,
                'eventos': eventos_por_dia.get(dia, []) if dia else [],
                'tem_evento': bool(eventos_por_dia.get(dia, [])) if dia else False,
                'is_today': dia == hoje_real.day and mes == hoje_real.month and ano == hoje_real.year,
            })
        calendario_semanas.append(linha)

    return {
        'mes_nome': nomes_meses[mes],
        'nomes_dias': nomes_dias,
        'calendario_semanas': calendario_semanas,
        'eventos_por_dia': eventos_por_dia,
    }  

def calendario_rh(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para visualizar o calendário do RH.'
    )
    if redirect_response:
        return redirect_response

    hoje = date.today()

    try:
        ano = int(request.GET.get('ano', hoje.year))
    except (TypeError, ValueError):
        ano = hoje.year

    try:
        mes = int(request.GET.get('mes', hoje.month))
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

    calendario_context = _montar_eventos_calendario_rh(empresa_ativa, ano, mes)

    lembretes = LembreteRH.objects.filter(
        empresa=empresa_ativa
    ).select_related('funcionario').order_by('data', 'titulo')[:12]

    context = {
        'ano': ano,
        'mes': mes,
        'ano_anterior': ano_anterior,
        'mes_anterior': mes_anterior,
        'ano_proximo': ano_proximo,
        'mes_proximo': mes_proximo,
        'lembretes': lembretes,
        **calendario_context,
    }
    return render(request, 'rh/calendario.html', context)

####################### CRUD LEMBRETES RH #################################

def lista_lembretes_rh(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para visualizar os lembretes.'
    )
    if redirect_response:
        return redirect_response

    lembretes = LembreteRH.objects.filter(
        empresa=empresa_ativa
    ).select_related('funcionario').order_by('data', 'titulo')

    return render(request, 'rh/lembretes/lista.html', {
        'lembretes': lembretes,
    })


def criar_lembrete_rh(request):
    empresa_ativa = request.empresa_ativa

    if request.method == 'POST':
        form = LembreteRHForm(request.POST, empresa_ativa=empresa_ativa)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa_ativa
            obj.save()

            lembretes = LembreteRH.objects.filter(
                empresa=empresa_ativa
            ).order_by('data')

            return render(request, 'rh/partials/lembretes_lista.html', {
                'lembretes': lembretes
            })

    form = LembreteRHForm(empresa_ativa=empresa_ativa)
    return render(request, 'rh/lembretes/form.html', {'form': form})


def editar_lembrete_rh(request, pk):
    empresa_ativa = request.empresa_ativa
    lembrete = get_object_or_404(LembreteRH, pk=pk, empresa=empresa_ativa)

    if request.method == 'POST':
        form = LembreteRHForm(request.POST, instance=lembrete, empresa_ativa=empresa_ativa)
        if form.is_valid():
            form.save()

            lembretes = LembreteRH.objects.filter(
                empresa=empresa_ativa
            ).order_by('data')

            return render(request, 'rh/partials/lembretes_lista.html', {
                'lembretes': lembretes
            })

    form = LembreteRHForm(instance=lembrete, empresa_ativa=empresa_ativa)
    return render(request, 'rh/lembretes/form.html', {
        'form': form,
        'lembrete': lembrete
    })

def excluir_lembrete_rh(request, pk):
    empresa_ativa = request.empresa_ativa
    lembrete = get_object_or_404(LembreteRH, pk=pk, empresa=empresa_ativa)

    lembrete.delete()

    lembretes = LembreteRH.objects.filter(
        empresa=empresa_ativa
    ).order_by('data')

    return render(request, 'rh/partials/lembretes_lista.html', {
        'lembretes': lembretes
    })


####################### DASHBOARD RH #################################

def dashboard_rh(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para visualizar o RH.'
    )
    if redirect_response:
        return redirect_response

    import calendar
    from datetime import date, timedelta
    from django.urls import reverse

    hoje = date.today()
    ano = hoje.year
    mes = hoje.month
    limite_experiencia = hoje - timedelta(days=45)

    funcionarios = Funcionario.objects.filter(
        empresa=empresa_ativa
    ).select_related(
        'cargo',
        'lotacao',
        'tipo_contrato',
    )

    total_funcionarios = funcionarios.count()

    # Em férias agora
    ferias_ativas_qs = FeriasFuncionario.objects.filter(
        funcionario__empresa=empresa_ativa,
        gozo_inicio__isnull=False,
        gozo_fim__isnull=False,
        gozo_inicio__lte=hoje,
        gozo_fim__gte=hoje,
    ).select_related('funcionario').order_by('gozo_fim')

    total_ferias = ferias_ativas_qs.values('funcionario_id').distinct().count()

    # Em experiência
    experiencia_qs = funcionarios.filter(
        Q(
            data_admissao__isnull=False,
            data_admissao__gte=limite_experiencia,
            inicio_prorrogacao__isnull=True
        ) |
        Q(
            inicio_prorrogacao__isnull=False,
            fim_prorrogacao__isnull=False,
            inicio_prorrogacao__lte=hoje,
            fim_prorrogacao__gte=hoje
        )
    ).order_by('nome')

    total_experiencia = experiencia_qs.count()

    # Em aviso
    aviso_qs = funcionarios.filter(
        data_inicio_aviso__isnull=False,
        data_fim_aviso__isnull=False,
        data_inicio_aviso__lte=hoje,
        data_fim_aviso__gte=hoje
    ).order_by('data_fim_aviso', 'nome')

    total_aviso = aviso_qs.count()

    eventos_por_dia = {}

    def add_evento(data_evento, tipo, label, funcionario=None):
        if not data_evento or data_evento.year != ano or data_evento.month != mes:
            return

        dia = data_evento.day
        detalhe_url = None
        if funcionario:
            detalhe_url = reverse('rh:detalhes_funcionario', args=[funcionario.pk])

        eventos_por_dia.setdefault(dia, []).append({
            'tipo': tipo,
            'label': label,
            'funcionario_nome': funcionario.nome if funcionario else '',
            'detalhe_url': detalhe_url,
        })

    # Férias
    ferias_mes = FeriasFuncionario.objects.filter(
        funcionario__empresa=empresa_ativa
    ).select_related('funcionario', 'funcionario__cargo')

    for item in ferias_mes:
        if item.gozo_inicio:
            add_evento(
                item.gozo_inicio,
                'ferias_inicio',
                'Início de férias',
                item.funcionario
            )
        if item.gozo_fim:
            add_evento(
                item.gozo_fim,
                'ferias_volta',
                'Volta de férias',
                item.funcionario
            )

    # Experiência / prorrogação
    experiencia_alertas = funcionarios.filter(
        data_admissao__isnull=False
    ).order_by('data_admissao')

    for func in experiencia_alertas:
        data_45 = func.data_admissao + timedelta(days=45)

        if data_45.month == mes and data_45.year == ano and not func.inicio_prorrogacao:
            add_evento(
                data_45,
                'experiencia_45',
                '45 dias / iniciar prorrogação',
                func
            )

        if func.fim_prorrogacao:
            add_evento(
                func.fim_prorrogacao,
                'fim_prorrogacao',
                'Fim da prorrogação',
                func
            )

    # Aviso
    aviso_mes = funcionarios.filter(
        data_fim_aviso__isnull=False
    ).order_by('data_fim_aviso')

    for func in aviso_mes:
        add_evento(
            func.data_fim_aviso,
            'fim_aviso',
            'Fim de aviso',
            func
        )

    # Exames
    exames_proximos = []
    for func in funcionarios.filter(data_admissao__isnull=False).order_by('nome'):
        aso_admissional = func.asos.filter(tipo='admissional').order_by('-data').first()
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
                'funcionario': func,
                'data': proximo_exame,
            })
            add_evento(
                proximo_exame,
                'exame',
                'Exame periódico',
                func
            )

    exames_proximos = sorted(exames_proximos, key=lambda x: x['data'])[:20]


    # Lembretes manuais no calendário da dashboard
    lembretes_dashboard = LembreteRH.objects.filter(
        empresa=empresa_ativa,
        # concluido=False
    ).select_related('funcionario').order_by('data', 'titulo')

    for item in lembretes_dashboard:
        add_evento(
            item.data,
            'lembrete',
            item.titulo,
            item.funcionario
        )

    # Ordena eventos do dia por tipo/nome
    for dia in eventos_por_dia:
        eventos_por_dia[dia] = sorted(
            eventos_por_dia[dia],
            key=lambda e: (e['label'], e['funcionario_nome'])
        )

    # Calendário em português
    nomes_meses = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }

    nomes_dias = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']

    cal = calendar.Calendar(firstweekday=6)  # domingo
    semanas_brutas = cal.monthdayscalendar(ano, mes)
    calendario_semanas = []

    for semana in semanas_brutas:
        linha = []
        for dia in semana:
            linha.append({
                'numero': dia,
                'eventos': eventos_por_dia.get(dia, []) if dia else [],
                'tem_evento': bool(eventos_por_dia.get(dia, [])) if dia else False,
                'is_today': dia == hoje.day,
            })
        calendario_semanas.append(linha)

    context = {
        'hoje': hoje,
        'mes_nome': nomes_meses[mes],
        'ano': ano,
        'nomes_dias': nomes_dias,

        'total_funcionarios': total_funcionarios,
        'total_ferias': total_ferias,
        'total_experiencia': total_experiencia,
        'total_aviso': total_aviso,

        'calendario_semanas': calendario_semanas,
        'eventos_por_dia': eventos_por_dia,

        'exames_proximos': exames_proximos[:8],
        'ferias_ativas': ferias_ativas_qs[:8],
        'experiencia_lista': experiencia_qs[:8],
        'aviso_lista': aviso_qs[:8],
    }
    return render(request, 'rh/dashboard.html', context)

def lista_funcionarios(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para visualizar os funcionários.'
    )
    if redirect_response:
        return redirect_response

    hoje = date.today()
    limite_experiencia = hoje - timedelta(days=45)

    funcionarios = Funcionario.objects.filter(
        empresa=empresa_ativa
    ).select_related(
        'empresa',
        'cargo',
        'lotacao',
        'tipo_contrato',
    )

    nome = request.GET.get('nome', '').strip()
    cargo_id = request.GET.get('cargo', '').strip()
    lotacao_id = request.GET.get('lotacao', '').strip()
    situacao = request.GET.get('situacao', '').strip()
    grupo = request.GET.get('grupo', '').strip()

    if nome:
        funcionarios = funcionarios.filter(
            Q(nome__icontains=nome) |
            Q(cpf__icontains=nome) |
            Q(pis__icontains=nome) |
            Q(matricula__icontains=nome)
        )

    if cargo_id:
        funcionarios = funcionarios.filter(cargo_id=cargo_id)

    if lotacao_id:
        funcionarios = funcionarios.filter(lotacao_id=lotacao_id)

    if situacao and situacao != 'todos':
        funcionarios = funcionarios.filter(situacao_atual=situacao)
    elif grupo == 'todos':
        pass
    elif grupo == 'ferias':
        funcionarios = funcionarios.filter(
            ferias__gozo_inicio__lte=hoje,
            ferias__gozo_fim__gte=hoje,
        ).distinct()
    elif grupo == 'experiencia':
        funcionarios = funcionarios.filter(
            Q(
                data_admissao__isnull=False,
                data_admissao__gte=limite_experiencia,
                inicio_prorrogacao__isnull=True
            ) |
            Q(
                inicio_prorrogacao__isnull=False,
                fim_prorrogacao__isnull=False,
                inicio_prorrogacao__lte=hoje,
                fim_prorrogacao__gte=hoje
            )
        ).distinct()
    elif grupo == 'aviso':
        funcionarios = funcionarios.filter(
            data_inicio_aviso__isnull=False,
            data_fim_aviso__isnull=False,
            data_inicio_aviso__lte=hoje,
            data_fim_aviso__gte=hoje
        )
    else:
        funcionarios = funcionarios.filter(situacao_atual='admitido')

    cargos = Cargo.objects.filter(empresa=empresa_ativa).order_by('nome')
    lotacoes = Lotacao.objects.filter(empresa=empresa_ativa).order_by('nome')

    context = {
        'funcionarios': funcionarios.order_by('nome'),
        'cargos': cargos,
        'lotacoes': lotacoes,
        'status_choices': Funcionario.STATUS_CHOICES,
        'total_funcionarios_filtrados': funcionarios.count(),
    }
    return render(request, 'rh/funcionarios/lista.html', context)

@transaction.atomic
def criar_funcionario(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de cadastrar funcionários.'
    )
    if redirect_response:
        return redirect_response

    if request.method == 'POST':
        form = FuncionarioForm(
            request.POST,
            request.FILES,
            empresa_ativa=empresa_ativa
        )
        formsets = _montar_formsets_funcionario(request=request, instance=None)

        if form.is_valid() and _todos_formsets_validos(formsets):
            funcionario = form.save(commit=False)
            funcionario.empresa = empresa_ativa
            funcionario.save()

            _salvar_todos_formsets(funcionario, formsets)

            messages.success(request, 'Funcionário cadastrado com sucesso.')
            return redirect('rh:detalhes_funcionario', pk=funcionario.pk)
    else:
        form = FuncionarioForm(empresa_ativa=empresa_ativa)
        formsets = _montar_formsets_funcionario()

    context = {
        'form': form,
        'titulo': 'Novo Funcionário',
        'subtitulo': 'Preencha os dados do colaborador e seus históricos.',
        **formsets,
    }
    return render(request, 'rh/funcionarios/form.html', context)

def _empresa_ativa_or_redirect(request, mensagem='Selecione uma empresa para continuar.'):
    empresa_ativa = getattr(request, 'empresa_ativa', None)
    if not empresa_ativa:
        messages.warning(request, mensagem)
        return None, redirect('selecionar_empresa')
    return empresa_ativa, None



def _get_funcionario_empresa(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return None, redirect_response

    funcionario = get_object_or_404(
        Funcionario,
        pk=pk,
        empresa=empresa_ativa
    )
    return funcionario, None

def _get_form_kwargs(request, empresa_ativa, instance=None):
    kwargs = {
        'instance': instance,
        'empresa_ativa': empresa_ativa,
    }
    if request.method == 'POST':
        kwargs['data'] = request.POST
        kwargs['files'] = request.FILES
    return kwargs


def _montar_forms_funcionario(request, empresa_ativa, funcionario):
    """
    Monta todos os forms principais da tela.
    """
    kwargs = _get_form_kwargs(request, empresa_ativa, instance=funcionario)

    return {
        'form_pessoais': FuncionarioDadosPessoaisForm(**kwargs),
        'form_admissao': FuncionarioAdmissaoForm(**kwargs),
        'form_demissao': FuncionarioDemissaoForm(**kwargs),
        'form_outros': FuncionarioOutrosForm(**kwargs),
    }


def _montar_formsets_funcionario_por_secao(request=None, instance=None, secao_post=None):
    """
    Monta os formsets.
    Se for POST, só vincula POST/FILES na seção enviada.
    As demais continuam em modo GET, para não invalidarem a tela inteira.
    """
    is_post = request is not None and request.method == 'POST'

    def bind_if(secao_nome, formset_class, prefix):
        if is_post and secao_post == secao_nome:
            return formset_class(
                request.POST,
                request.FILES,
                instance=instance,
                prefix=prefix,
            )
        return formset_class(
            instance=instance,
            prefix=prefix,
        )

    return {
        'ferias_formset': bind_if('ferias', FeriasFuncionarioFormSet, 'ferias'),
        'afastamento_formset': bind_if('afastamentos', AfastamentoFuncionarioFormSet, 'afastamentos'),
        'dependente_formset': bind_if('dependentes', DependenteFormSet, 'dependentes'),
        'aso_formset': bind_if('saude', ASOFuncionarioFormSet, 'asos'),
        'certificado_formset': bind_if('saude', CertificadoFuncionarioFormSet, 'certificados'),
        'pcmso_formset': bind_if('saude', PCMSOFuncionarioFormSet, 'pcmso'),
        'atestado_licenca_formset': bind_if('saude', AtestadoLicencaFuncionarioFormSet, 'atestados_licencas'),
        'ocorrencia_saude_formset': bind_if('saude', OcorrenciaSaudeFuncionarioFormSet, 'ocorrencias_saude'),
    }


def _salvar_secao_funcionario(secao, forms, formsets, funcionario, empresa_ativa):
    """
    Salva apenas a seção enviada.
    Retorna (salvou_com_sucesso: bool, mensagem: str)
    """

    if secao == 'pessoais':
        form = forms['form_pessoais']
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa_ativa
            obj.save()
            return True, 'Dados pessoais atualizados com sucesso.'
        return False, 'Corrija os erros em Dados Pessoais.'

    if secao == 'admissao':
        form = forms['form_admissao']
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa_ativa
            obj.save()
            return True, 'Dados de admissão atualizados com sucesso.'
        return False, 'Corrija os erros em Admissão.'

    if secao == 'demissao':
        form = forms['form_demissao']
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa_ativa

            if obj.data_demissao:
                obj.situacao_atual = 'demitido'
            elif obj.situacao_atual == 'demitido':
                obj.situacao_atual = 'admitido'

            obj.save()
            return True, 'Dados de demissão atualizados com sucesso.'
        return False, 'Corrija os erros em Demissão.'

    if secao == 'outros':
        form = forms['form_outros']
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa_ativa
            obj.save()
            return True, 'Outros dados atualizados com sucesso.'
        return False, 'Corrija os erros em Outros Dados.'

    if secao == 'ferias':
        formset = formsets['ferias_formset']
        if formset.is_valid():
            formset.instance = funcionario
            formset.save()
            return True, 'Férias atualizadas com sucesso.'
        return False, 'Corrija os erros em Férias.'

    if secao == 'afastamentos':
        formset = formsets['afastamento_formset']
        if formset.is_valid():
            formset.instance = funcionario
            formset.save()
            return True, 'Afastamentos atualizados com sucesso.'
        return False, 'Corrija os erros em Afastamentos.'

    if secao == 'dependentes':
        formset = formsets['dependente_formset']
        if formset.is_valid():
            formset.instance = funcionario
            formset.save()
            return True, 'Dependentes atualizados com sucesso.'
        return False, 'Corrija os erros em Dependentes.'

    if secao == 'saude':
        formsets_saude = [
            formsets['aso_formset'],
            formsets['certificado_formset'],
            formsets['pcmso_formset'],
            formsets['atestado_licenca_formset'],
            formsets['ocorrencia_saude_formset'],
        ]

        if all(fs.is_valid() for fs in formsets_saude):
            for fs in formsets_saude:
                fs.instance = funcionario
                fs.save()
            return True, 'Dados de saúde atualizados com sucesso.'
        return False, 'Corrija os erros em Saúde.'

    return False, 'Seção inválida.'

@transaction.atomic
def editar_funcionario(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(
        Funcionario.objects.select_related(
            'empresa',
            'cargo',
            'lotacao',
            'tipo_contrato',
            'banco',
        ).prefetch_related(
            'dependentes',
            'ferias',
            'afastamentos',
            'asos',
            'certificados',
            'pcmso_registros',
            'atestados_licencas',
            'ocorrencias_saude',
        ),
        pk=pk,
        empresa=empresa_ativa
    )

    secao = request.POST.get('secao') if request.method == 'POST' else 'pessoais'

    forms = _montar_forms_funcionario(request, empresa_ativa, funcionario)
    formsets = _montar_formsets_funcionario_por_secao(
        request=request,
        instance=funcionario,
        secao_post=secao,
    )

    if request.method == 'POST':
        salvou, mensagem = _salvar_secao_funcionario(
            secao=secao,
            forms=forms,
            formsets=formsets,
            funcionario=funcionario,
            empresa_ativa=empresa_ativa,
        )

        if salvou:
            messages.success(request, mensagem)
            return redirect('rh:editar_funcionario', pk=funcionario.pk)

        messages.error(request, mensagem)

        # Recria tudo para manter a tela completa após erro,
        # mas preservando a seção atual com POST.
        forms = _montar_forms_funcionario(request, empresa_ativa, funcionario)
        formsets = _montar_formsets_funcionario_por_secao(
            request=request,
            instance=funcionario,
            secao_post=secao,
        )
    else:
        forms = _montar_forms_funcionario(request, empresa_ativa, funcionario)
        formsets = _montar_formsets_funcionario_por_secao(
            request=None,
            instance=funcionario,
            secao_post=None,
        )

    context = {
        'titulo': 'Editar Funcionário',
        'subtitulo': f'Atualize os dados de {funcionario.nome} por seção.',
        'funcionario': funcionario,
        'secao_ativa': secao,
        **forms,
        **formsets,
    }
    return render(request, 'rh/funcionarios/form.html', context)

def detalhes_funcionario(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response
    
    

    funcionario = get_object_or_404(
        Funcionario.objects.select_related(
            'empresa',
            'cargo',
            'lotacao',
            'tipo_contrato',
            'banco',
        ).prefetch_related(
            'dependentes',
            'ferias',
            'afastamentos',
            'asos',
            'certificados',
            'pcmso_registros',
            'atestados_licencas',
            'ocorrencias_saude',
        ),
        pk=pk,
        empresa=empresa_ativa
    )

    data_admissao = funcionario.data_admissao
    data_demissao = funcionario.data_demissao

    precisa_exame_demissional = False
    exame_info_indisponivel = False

    if data_admissao and data_demissao:
        precisa_exame_demissional = (data_demissao - data_admissao).days > 90
    else:
        exame_info_indisponivel = True

    historicos = funcionario.historicos.select_related('usuario').all()


    context = {
        'funcionario': funcionario,
        "precisa_exame_demissional": precisa_exame_demissional,
        "exame_info_indisponivel": exame_info_indisponivel,
        'historicos': historicos,
    }
    context.update(secao_anexos_context(funcionario))
    return render(request, 'rh/funcionarios/detalhes.html', context)


# caso sua URL antiga ainda aponte para detalhar_funcionario
detalhar_funcionario = detalhes_funcionario


def excluir_funcionario(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(
        Funcionario,
        pk=pk,
        empresa=empresa_ativa
    )

    if request.method == 'POST':
        funcionario.delete()
        messages.success(request, 'Funcionário excluído com sucesso.')
        return redirect('rh:lista_funcionarios')

    context = {
        'funcionario': funcionario
    }
    return render(request, 'rh/funcionarios/confirmar_exclusao.html', context)


def lista_cargos(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa para visualizar os cargos.'
    )
    if redirect_response:
        return redirect_response

    q = request.GET.get('q', '').strip()

    cargos = Cargo.objects.filter(empresa=empresa_ativa)

    if q:
        cargos = cargos.filter(nome__icontains=q)

    cargos = cargos.annotate(total_funcionarios=Count('funcionarios')).order_by('nome')

    context = {
        'cargos': cargos,
        'q': q,
    }
    return render(request, 'rh/cargos/lista.html', context)


def criar_cargo(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de cadastrar cargos.'
    )
    if redirect_response:
        return redirect_response

    if request.method == 'POST':
        form = CargoForm(request.POST)
        if form.is_valid():
            cargo = form.save(commit=False)
            cargo.empresa = empresa_ativa
            cargo.save()
            messages.success(request, 'Cargo cadastrado com sucesso.')
            return redirect('rh:lista_cargos')
    else:
        form = CargoForm()

    context = {
        'form': form,
        'titulo': 'Novo Cargo',
        'subtitulo': 'Cadastre um novo cargo para a empresa ativa.',
    }
    return render(request, 'rh/cargos/form.html', context)


def editar_cargo(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    cargo = get_object_or_404(Cargo, pk=pk, empresa=empresa_ativa)

    if request.method == 'POST':
        form = CargoForm(request.POST, instance=cargo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cargo atualizado com sucesso.')
            return redirect('rh:lista_cargos')
    else:
        form = CargoForm(instance=cargo)

    context = {
        'form': form,
        'titulo': 'Editar Cargo',
        'subtitulo': 'Atualize as informações do cargo.',
        'cargo': cargo,
    }
    return render(request, 'rh/cargos/form.html', context)


def excluir_cargo(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    cargo = get_object_or_404(Cargo, pk=pk, empresa=empresa_ativa)

    if request.method == 'POST':
        if cargo.funcionarios.exists():
            messages.error(
                request,
                'Este cargo não pode ser excluído porque existem funcionários vinculados a ele.'
            )
            return redirect('rh:lista_cargos')

        cargo.delete()
        messages.success(request, 'Cargo excluído com sucesso.')
        return redirect('rh:lista_cargos')

    context = {
        'cargo': cargo,
    }
    return render(request, 'rh/cargos/confirmar_exclusao.html', context)


def lista_lotacoes(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa.'
    )
    if redirect_response:
        return redirect_response

    q = request.GET.get('q', '').strip()

    lotacoes = Lotacao.objects.filter(empresa=empresa_ativa)

    if q:
        lotacoes = lotacoes.filter(nome__icontains=q)

    lotacoes = lotacoes.annotate(total_funcionarios=Count('funcionarios')).order_by('nome')

    context = {
        'lotacoes': lotacoes,
        'q': q,
    }
    return render(request, 'rh/lotacoes/lista.html', context)


def criar_lotacao(request):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa.'
    )
    if redirect_response:
        return redirect_response

    if request.method == 'POST':
        form = LotacaoForm(request.POST)
        if form.is_valid():
            lotacao = form.save(commit=False)
            lotacao.empresa = empresa_ativa
            lotacao.save()

            messages.success(request, 'Lotação cadastrada com sucesso.')
            return redirect('rh:lista_lotacoes')
    else:
        form = LotacaoForm()

    context = {
        'form': form,
        'titulo': 'Nova Lotação',
        'subtitulo': 'Cadastre uma nova lotação.',
    }
    return render(request, 'rh/lotacoes/form.html', context)


def editar_lotacao(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa.'
    )
    if redirect_response:
        return redirect_response

    lotacao = get_object_or_404(
        Lotacao,
        pk=pk,
        empresa=empresa_ativa
    )

    if request.method == 'POST':
        form = LotacaoForm(request.POST, instance=lotacao)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lotação atualizada com sucesso.')
            return redirect('rh:lista_lotacoes')
    else:
        form = LotacaoForm(instance=lotacao)

    context = {
        'form': form,
        'titulo': 'Editar Lotação',
        'subtitulo': 'Atualize os dados da lotação.',
        'lotacao': lotacao,
    }
    return render(request, 'rh/lotacoes/form.html', context)


def excluir_lotacao(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa.'
    )
    if redirect_response:
        return redirect_response

    lotacao = get_object_or_404(
        Lotacao,
        pk=pk,
        empresa=empresa_ativa
    )

    if request.method == 'POST':
        if lotacao.funcionarios.exists():
            messages.error(
                request,
                'Esta lotação possui funcionários vinculados.'
            )
            return redirect('rh:lista_lotacoes')

        lotacao.delete()
        messages.success(request, 'Lotação excluída com sucesso.')
        return redirect('rh:lista_lotacoes')

    context = {
        'lotacao': lotacao
    }
    return render(request, 'rh/lotacoes/confirmar_exclusao.html', context)



def modal_editar_pessoais(request, pk):
    funcionario = get_object_or_404(Funcionario, pk=pk)

    if request.method == "POST":
        form = FuncionarioDadosPessoaisForm(
            request.POST,
            request.FILES,
            instance=funcionario
        )
        if form.is_valid():
            form.save()
            response = render(
                request,
                "rh/funcionarios/modals/pessoais_success.html",
                {"funcionario": funcionario},
            )
            response["HX-Trigger-After-Settle"] = json.dumps({
    "closeSectionModal": True,
    "openSection": {"section": "pessoais"}
})
            return response
    else:
        form = FuncionarioDadosPessoaisForm(instance=funcionario)

    return render(
        request,
        "rh/funcionarios/modals/modal_pessoais_form.html",
        {
            "funcionario": funcionario,
            "form": form,
        },
    )

import json

from django.shortcuts import get_object_or_404, render

from rh.forms import FuncionarioAdmissaoForm
from rh.models import Funcionario
from rh.utils.historico import registrar_alteracao_situacao


def modal_editar_admissao(request, pk):
    funcionario = get_object_or_404(Funcionario, pk=pk)

    if request.method == "POST":
        situacao_antiga = funcionario.situacao_atual

        form = FuncionarioAdmissaoForm(
            request.POST,
            request.FILES,
            instance=funcionario,
            empresa_ativa=getattr(request, "empresa_ativa", None),
        )

        if form.is_valid():
            funcionario = form.save()
            situacao_nova = funcionario.situacao_atual

            registrar_alteracao_situacao(
                funcionario=funcionario,
                usuario=request.user,
                situacao_antiga=situacao_antiga,
                situacao_nova=situacao_nova,
            )

            response = render(
                request,
                "rh/funcionarios/modals/admissao_success.html",
                {"funcionario": funcionario},
            )
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "admissao"}
            })
            return response
    else:
        form = FuncionarioAdmissaoForm(
            instance=funcionario,
            empresa_ativa=getattr(request, "empresa_ativa", None),
        )

    return render(
        request,
        "rh/funcionarios/modals/modal_admissao_form.html",
        {
            "funcionario": funcionario,
            "form": form,
        },
    )


def modal_editar_demissao(request, pk):
    funcionario = get_object_or_404(Funcionario, pk=pk)

    if request.method == "POST":
        form = FuncionarioDemissaoForm(
            request.POST,
            request.FILES,
            instance=funcionario
        )
    else:
        form = FuncionarioDemissaoForm(instance=funcionario)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)

        if obj.data_demissao:
            obj.situacao_atual = 'demitido'
        elif obj.situacao_atual == 'demitido':
            obj.situacao_atual = 'admitido'

        obj.save()
        funcionario.refresh_from_db()

        response = render(
            request,
            "rh/funcionarios/modals/demissao_success.html",
            {"funcionario": funcionario}
        )
        response["HX-Trigger-After-Settle"] = json.dumps({
            "closeSectionModal": True,
            "openSection": {"section": "demissao"}
        })
        return response

    # calcula a lógica do exame com base na data que está no form,
    # mesmo antes de salvar, para o alerta do modal ficar correto
    data_admissao = funcionario.data_admissao
    data_demissao = funcionario.data_demissao
    exame_info_indisponivel = False
    precisa_exame_demissional = False

    if request.method == "POST":
        valor_data_demissao = form.data.get("data_demissao")
        if valor_data_demissao:
            try:
                data_demissao = datetime.strptime(valor_data_demissao, "%Y-%m-%d").date()
            except ValueError:
                data_demissao = funcionario.data_demissao

    if data_admissao and data_demissao:
        precisa_exame_demissional = (data_demissao - data_admissao).days > 90
    else:
        exame_info_indisponivel = True

    return render(
        request,
        "rh/funcionarios/modals/modal_demissao_form.html",
        {
            "form": form,
            "funcionario": funcionario,
            "precisa_exame_demissional": precisa_exame_demissional,
            "exame_info_indisponivel": exame_info_indisponivel,
        }
    )

def modal_editar_bancarios(request, pk):
    funcionario = get_object_or_404(Funcionario, pk=pk)

    if request.method == "POST":
        form = FuncionarioBancariosForm(request.POST, instance=funcionario)

        if form.is_valid():
            form.save()
            funcionario.refresh_from_db()

            response = render(
                request,
                "rh/funcionarios/modals/bancarios_success.html",
                {"funcionario": funcionario}
            )

            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "bancarios"}
            })

            return response
    else:
        form = FuncionarioBancariosForm(instance=funcionario)

    return render(
        request,
        "rh/funcionarios/modals/modal_bancarios_form.html",
        {
            "form": form,
            "funcionario": funcionario
        }
    )

def modal_editar_outros(request, pk):
    funcionario = get_object_or_404(Funcionario, pk=pk)

    if request.method == "POST":
        form = FuncionarioOutrosForm(request.POST, instance=funcionario)

        if form.is_valid():
            form.save()
            funcionario.refresh_from_db()

            response = render(
                request,
                "rh/funcionarios/modals/outros_success.html",
                {"funcionario": funcionario}
            )

            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "outros"}
            })

            return response
    else:
        form = FuncionarioOutrosForm(instance=funcionario)

    return render(
        request,
        "rh/funcionarios/modals/modal_outros_form.html",
        {
            "form": form,
            "funcionario": funcionario
        }
    )

def _render_ferias_list(request, funcionario):
    return render(
        request,
        "rh/funcionarios/includes/partials/ferias_lista.html",
        {
            "funcionario": funcionario,
            "ferias_list": funcionario.ferias.all(),
        },
    )


def ferias_lista(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(
        Funcionario.objects.prefetch_related('ferias'),
        pk=pk,
        empresa=empresa_ativa
    )

    return _render_ferias_list(request, funcionario)


def modal_adicionar_ferias(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)

    if request.method == "POST":
        form = FeriasModalForm(request.POST)
        if form.is_valid():
            ferias = form.save(commit=False)
            ferias.funcionario = funcionario
            ferias.save()
            funcionario.refresh_from_db()

            response = _render_ferias_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "ferias"}
            })
            return response
    else:
        form = FeriasModalForm()

    return render(
        request,
        "rh/funcionarios/modals/modal_ferias_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Adicionar férias",
            "modo": "criar",
            "item": None,
        },
    )


def modal_editar_ferias(request, pk, ferias_id):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(
        FeriasFuncionario,
        pk=ferias_id,
        funcionario=funcionario
    )

    if request.method == "POST":
        form = FeriasModalForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            funcionario.refresh_from_db()

            response = _render_ferias_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "ferias"}
            })
            return response
    else:
        form = FeriasModalForm(instance=item)

    return render(
        request,
        "rh/funcionarios/modals/modal_ferias_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Editar férias",
            "modo": "editar",
            "item": item,
        },
    )


def modal_excluir_ferias(request, pk, ferias_id):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(
        FeriasFuncionario,
        pk=ferias_id,
        funcionario=funcionario
    )

    if request.method == "POST":
        item.delete()
        funcionario.refresh_from_db()

        response = _render_ferias_list(request, funcionario)
        response["HX-Trigger-After-Settle"] = json.dumps({
            "closeSectionModal": True,
            "openSection": {"section": "ferias"}
        })
        return response

    return render(
        request,
        "rh/funcionarios/modals/modal_ferias_confirm_delete.html",
        {
            "funcionario": funcionario,
            "item": item,
        },
    )

def _render_afastamentos_list(request, funcionario):
    return render(
        request,
        "rh/funcionarios/includes/partials/afastamentos_lista.html",
        {
            "funcionario": funcionario,
            "afastamentos_list": funcionario.afastamentos.all(),
        },
    )


def afastamentos_lista(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(
        Funcionario.objects.prefetch_related('afastamentos'),
        pk=pk,
        empresa=empresa_ativa
    )

    return _render_afastamentos_list(request, funcionario)


def modal_adicionar_afastamento(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)

    if request.method == "POST":
        form = AfastamentoFuncionarioForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.funcionario = funcionario
            item.save()
            funcionario.refresh_from_db()

            response = _render_afastamentos_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "afastamentos"}
            })
            return response
    else:
        form = AfastamentoFuncionarioForm()

    return render(
        request,
        "rh/funcionarios/modals/modal_afastamento_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Adicionar afastamento",
            "modo": "criar",
            "item": None,
        },
    )


def modal_editar_afastamento(request, pk, afastamento_id):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(
        AfastamentoFuncionario,
        pk=afastamento_id,
        funcionario=funcionario
    )

    if request.method == "POST":
        form = AfastamentoFuncionarioForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            funcionario.refresh_from_db()

            response = _render_afastamentos_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "afastamentos"}
            })
            return response
    else:
        form = AfastamentoFuncionarioForm(instance=item)

    return render(
        request,
        "rh/funcionarios/modals/modal_afastamento_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Editar afastamento",
            "modo": "editar",
            "item": item,
        },
    )


def modal_excluir_afastamento(request, pk, afastamento_id):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(
        AfastamentoFuncionario,
        pk=afastamento_id,
        funcionario=funcionario
    )

    if request.method == "POST":
        item.delete()
        funcionario.refresh_from_db()

        response = _render_afastamentos_list(request, funcionario)
        response["HX-Trigger-After-Settle"] = json.dumps({
            "closeSectionModal": True,
            "openSection": {"section": "afastamentos"}
        })
        return response

    return render(
        request,
        "rh/funcionarios/modals/modal_afastamento_confirm_delete.html",
        {
            "funcionario": funcionario,
            "item": item,
        },
    )

def _render_afastamentos_list(request, funcionario):
    return render(
        request,
        "rh/funcionarios/includes/partials/afastamentos_lista.html",
        {
            "funcionario": funcionario,
            "afastamentos_list": funcionario.afastamentos.all(),
        },
    )


def afastamentos_lista(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(
        Funcionario.objects.prefetch_related('afastamentos'),
        pk=pk,
        empresa=empresa_ativa
    )

    return _render_afastamentos_list(request, funcionario)


def modal_adicionar_afastamento(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)

    if request.method == "POST":
        form = AfastamentoFuncionarioForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.funcionario = funcionario
            item.save()
            funcionario.refresh_from_db()

            response = _render_afastamentos_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "afastamentos"}
            })
            return response
    else:
        form = AfastamentoFuncionarioForm()

    return render(
        request,
        "rh/funcionarios/modals/modal_afastamento_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Adicionar afastamento",
            "modo": "criar",
            "item": None,
        },
    )


def modal_editar_afastamento(request, pk, afastamento_id):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(
        AfastamentoFuncionario,
        pk=afastamento_id,
        funcionario=funcionario
    )

    if request.method == "POST":
        form = AfastamentoFuncionarioForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            funcionario.refresh_from_db()

            response = _render_afastamentos_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "afastamentos"}
            })
            return response
    else:
        form = AfastamentoFuncionarioForm(instance=item)

    return render(
        request,
        "rh/funcionarios/modals/modal_afastamento_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Editar afastamento",
            "modo": "editar",
            "item": item,
        },
    )


def modal_excluir_afastamento(request, pk, afastamento_id):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(
        AfastamentoFuncionario,
        pk=afastamento_id,
        funcionario=funcionario
    )

    if request.method == "POST":
        item.delete()
        funcionario.refresh_from_db()

        response = _render_afastamentos_list(request, funcionario)
        response["HX-Trigger-After-Settle"] = json.dumps({
            "closeSectionModal": True,
            "openSection": {"section": "afastamentos"}
        })
        return response

    return render(
        request,
        "rh/funcionarios/modals/modal_afastamento_confirm_delete.html",
        {
            "funcionario": funcionario,
            "item": item,
        },
    )


########################### DEPENDENTES #########################################

def _render_dependentes_list(request, funcionario):
    return render(
        request,
        "rh/funcionarios/includes/partials/dependentes_lista.html",
        {
            "funcionario": funcionario,
            "dependentes_list": funcionario.dependentes.all(),
        },
    )


def dependentes_lista(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(
        Funcionario.objects.prefetch_related('dependentes'),
        pk=pk,
        empresa=empresa_ativa
    )

    return _render_dependentes_list(request, funcionario)


def modal_adicionar_dependente(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)

    if request.method == "POST":
        form = DependenteForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.funcionario = funcionario
            item.save()
            funcionario.refresh_from_db()

            response = _render_dependentes_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "dependentes"}
            })
            return response
    else:
        form = DependenteForm()

    return render(
        request,
        "rh/funcionarios/modals/modal_dependente_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Adicionar dependente",
            "modo": "criar",
            "item": None,
        },
    )


def modal_editar_dependente(request, pk, dependente_id):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(
        Dependente,
        pk=dependente_id,
        funcionario=funcionario
    )

    if request.method == "POST":
        form = DependenteForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            funcionario.refresh_from_db()

            response = _render_dependentes_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "dependentes"}
            })
            return response
    else:
        form = DependenteForm(instance=item)

    return render(
        request,
        "rh/funcionarios/modals/modal_dependente_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Editar dependente",
            "modo": "editar",
            "item": item,
        },
    )


def modal_excluir_dependente(request, pk, dependente_id):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        'Selecione uma empresa antes de continuar.'
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(
        Dependente,
        pk=dependente_id,
        funcionario=funcionario
    )

    if request.method == "POST":
        item.delete()
        funcionario.refresh_from_db()

        response = _render_dependentes_list(request, funcionario)
        response["HX-Trigger-After-Settle"] = json.dumps({
            "closeSectionModal": True,
            "openSection": {"section": "dependentes"}
        })
        return response

    return render(
        request,
        "rh/funcionarios/modals/modal_dependente_confirm_delete.html",
        {
            "funcionario": funcionario,
            "item": item,
        },
    )


################################ SAÚDE ##############################################

################################ ASO ##############################################


def _render_aso_list(request, funcionario):
    return render(
        request,
        "rh/funcionarios/includes/partials/aso_lista.html",
        {
            "funcionario": funcionario,
            "asos_list": funcionario.asos.all().order_by("-data", "-id"),
        },
    )


def aso_lista(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar."
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(
        Funcionario.objects.prefetch_related("asos"),
        pk=pk,
        empresa=empresa_ativa
    )

    return _render_aso_list(request, funcionario)


def modal_adicionar_aso(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar."
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)

    if request.method == "POST":
        form = ASOFuncionarioForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.funcionario = funcionario
            item.save()
            funcionario.refresh_from_db()

            response = _render_aso_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "saude"},
                "openHealthTab": {"tab": "aso"},
            })
            return response
    else:
        form = ASOFuncionarioForm()

    return render(
        request,
        "rh/funcionarios/modals/modal_aso_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Adicionar ASO",
            "modo": "criar",
            "item": None,
        },
    )


def modal_editar_aso(request, pk, aso_id):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar."
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(ASOFuncionario, pk=aso_id, funcionario=funcionario)

    if request.method == "POST":
        form = ASOFuncionarioForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            funcionario.refresh_from_db()

            response = _render_aso_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "saude"},
                "openHealthTab": {"tab": "aso"},
            })
            return response
    else:
        form = ASOFuncionarioForm(instance=item)

    return render(
        request,
        "rh/funcionarios/modals/modal_aso_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Editar ASO",
            "modo": "editar",
            "item": item,
        },
    )


def modal_excluir_aso(request, pk, aso_id):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar."
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(ASOFuncionario, pk=aso_id, funcionario=funcionario)

    if request.method == "POST":
        item.delete()
        funcionario.refresh_from_db()

        response = _render_aso_list(request, funcionario)
        response["HX-Trigger-After-Settle"] = json.dumps({
            "closeSectionModal": True,
            "openSection": {"section": "saude"},
            "openHealthTab": {"tab": "aso"},
        })
        return response

    return render(
        request,
        "rh/funcionarios/modals/modal_aso_confirm_delete.html",
        {
            "funcionario": funcionario,
            "item": item,
        },
    )

######################## CERTIFICADOS ####################################

def _render_certificados_list(request, funcionario):
    return render(
        request,
        "rh/funcionarios/includes/partials/certificados_lista.html",
        {
            "funcionario": funcionario,
            "certificados_list": funcionario.certificados.all().order_by("-data", "-id"),
        },
    )


def certificados_lista(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar."
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(
        Funcionario.objects.prefetch_related("certificados"),
        pk=pk,
        empresa=empresa_ativa
    )

    return _render_certificados_list(request, funcionario)


def modal_adicionar_certificado(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar."
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)

    if request.method == "POST":
        form = CertificadoFuncionarioForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.funcionario = funcionario
            item.save()
            funcionario.refresh_from_db()

            response = _render_certificados_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "saude"},
                "openHealthTab": {"tab": "certificados"},
            })
            return response
    else:
        form = CertificadoFuncionarioForm()

    return render(
        request,
        "rh/funcionarios/modals/modal_certificado_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Adicionar certificado",
            "modo": "criar",
            "item": None,
        },
    )


def modal_editar_certificado(request, pk, certificado_id):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar."
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(CertificadoFuncionario, pk=certificado_id, funcionario=funcionario)

    if request.method == "POST":
        form = CertificadoFuncionarioForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            funcionario.refresh_from_db()

            response = _render_certificados_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "saude"},
                "openHealthTab": {"tab": "certificados"},
            })
            return response
    else:
        form = CertificadoFuncionarioForm(instance=item)

    return render(
        request,
        "rh/funcionarios/modals/modal_certificado_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Editar certificado",
            "modo": "editar",
            "item": item,
        },
    )


def modal_excluir_certificado(request, pk, certificado_id):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar."
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(CertificadoFuncionario, pk=certificado_id, funcionario=funcionario)

    if request.method == "POST":
        item.delete()
        funcionario.refresh_from_db()

        response = _render_certificados_list(request, funcionario)
        response["HX-Trigger-After-Settle"] = json.dumps({
            "closeSectionModal": True,
            "openSection": {"section": "saude"},
            "openHealthTab": {"tab": "certificados"},
        })
        return response

    return render(
        request,
        "rh/funcionarios/modals/modal_certificado_confirm_delete.html",
        {
            "funcionario": funcionario,
            "item": item,
        },
    )

############################ PCMSO ##################################

def _render_pcmso_list(request, funcionario):
    return render(
        request,
        "rh/funcionarios/includes/partials/pcmso_lista.html",
        {
            "funcionario": funcionario,
            "pcmso_list": funcionario.pcmso_registros.all().order_by("-data_vencimento", "-id"),
        },
    )


def pcmso_lista(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar."
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(
        Funcionario.objects.prefetch_related("pcmso_registros"),
        pk=pk,
        empresa=empresa_ativa
    )

    return _render_pcmso_list(request, funcionario)


def modal_adicionar_pcmso(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar."
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)

    if request.method == "POST":
        form = PCMSOFuncionarioForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.funcionario = funcionario
            item.save()
            funcionario.refresh_from_db()

            response = _render_pcmso_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "saude"},
                "openHealthTab": {"tab": "pcmso"},
            })
            return response
    else:
        form = PCMSOFuncionarioForm()

    return render(
        request,
        "rh/funcionarios/modals/modal_pcmso_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Adicionar PCMSO",
            "modo": "criar",
            "item": None,
        },
    )


def modal_editar_pcmso(request, pk, pcmso_id):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar."
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(PCMSOFuncionario, pk=pcmso_id, funcionario=funcionario)

    if request.method == "POST":
        form = PCMSOFuncionarioForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            funcionario.refresh_from_db()

            response = _render_pcmso_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "saude"},
                "openHealthTab": {"tab": "pcmso"},
            })
            return response
    else:
        form = PCMSOFuncionarioForm(instance=item)

    return render(
        request,
        "rh/funcionarios/modals/modal_pcmso_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Editar PCMSO",
            "modo": "editar",
            "item": item,
        },
    )


def modal_excluir_pcmso(request, pk, pcmso_id):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar."
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(PCMSOFuncionario, pk=pcmso_id, funcionario=funcionario)

    if request.method == "POST":
        item.delete()
        funcionario.refresh_from_db()

        response = _render_pcmso_list(request, funcionario)
        response["HX-Trigger-After-Settle"] = json.dumps({
            "closeSectionModal": True,
            "openSection": {"section": "saude"},
            "openHealthTab": {"tab": "pcmso"},
        })
        return response

    return render(
        request,
        "rh/funcionarios/modals/modal_pcmso_confirm_delete.html",
        {
            "funcionario": funcionario,
            "item": item,
        },
    )

#################### ATESTADOS #######################################

def _render_atestados_licencas_list(request, funcionario):
    return render(
        request,
        "rh/funcionarios/includes/partials/atestados_licencas_lista.html",
        {
            "funcionario": funcionario,
            "atestados_list": funcionario.atestados_licencas.all().order_by("-data", "-id"),
        },
    )


def atestados_licencas_lista(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar."
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(
        Funcionario.objects.prefetch_related("atestados_licencas"),
        pk=pk,
        empresa=empresa_ativa
    )

    return _render_atestados_licencas_list(request, funcionario)


def modal_adicionar_atestado_licenca(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar."
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)

    if request.method == "POST":
        form = AtestadoLicencaFuncionarioForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.funcionario = funcionario
            item.save()
            funcionario.refresh_from_db()

            response = _render_atestados_licencas_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "saude"},
                "openHealthTab": {"tab": "atestados"},
            })
            return response
    else:
        form = AtestadoLicencaFuncionarioForm()

    return render(
        request,
        "rh/funcionarios/modals/modal_atestado_licenca_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Adicionar atestado / licença",
            "modo": "criar",
            "item": None,
        },
    )


def modal_editar_atestado_licenca(request, pk, atestado_id):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar."
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(
        AtestadoLicencaFuncionario,
        pk=atestado_id,
        funcionario=funcionario
    )

    if request.method == "POST":
        form = AtestadoLicencaFuncionarioForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            funcionario.refresh_from_db()

            response = _render_atestados_licencas_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "saude"},
                "openHealthTab": {"tab": "atestados"},
            })
            return response
    else:
        form = AtestadoLicencaFuncionarioForm(instance=item)

    return render(
        request,
        "rh/funcionarios/modals/modal_atestado_licenca_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Editar atestado / licença",
            "modo": "editar",
            "item": item,
        },
    )


def modal_excluir_atestado_licenca(request, pk, atestado_id):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar."
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(
        AtestadoLicencaFuncionario,
        pk=atestado_id,
        funcionario=funcionario
    )

    if request.method == "POST":
        item.delete()
        funcionario.refresh_from_db()

        response = _render_atestados_licencas_list(request, funcionario)
        response["HX-Trigger-After-Settle"] = json.dumps({
            "closeSectionModal": True,
            "openSection": {"section": "saude"},
            "openHealthTab": {"tab": "atestados"},
        })
        return response

    return render(
        request,
        "rh/funcionarios/modals/modal_atestado_licenca_confirm_delete.html",
        {
            "funcionario": funcionario,
            "item": item,
        },
    )

##############################   OCORRENCIAS   ##########################

def _render_ocorrencias_saude_list(request, funcionario):
    return render(
        request,
        "rh/funcionarios/includes/partials/ocorrencias_saude_lista.html",
        {
            "funcionario": funcionario,
            "ocorrencias_list": funcionario.ocorrencias_saude.all().order_by("-data", "-criado_em"),
        },
    )


def ocorrencias_saude_lista(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar."
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(
        Funcionario.objects.prefetch_related("ocorrencias_saude"),
        pk=pk,
        empresa=empresa_ativa
    )

    return _render_ocorrencias_saude_list(request, funcionario)


def modal_adicionar_ocorrencia_saude(request, pk):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar."
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)

    if request.method == "POST":
        form = OcorrenciaSaudeFuncionarioForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.funcionario = funcionario
            item.save()
            funcionario.refresh_from_db()

            response = _render_ocorrencias_saude_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "saude"},
                "openHealthTab": {"tab": "ocorrencias"},
            })
            return response
    else:
        form = OcorrenciaSaudeFuncionarioForm()

    return render(
        request,
        "rh/funcionarios/modals/modal_ocorrencia_saude_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Adicionar ocorrência de saúde",
            "modo": "criar",
            "item": None,
        },
    )


def modal_editar_ocorrencia_saude(request, pk, ocorrencia_id):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar."
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(
        OcorrenciaSaudeFuncionario,
        pk=ocorrencia_id,
        funcionario=funcionario
    )

    if request.method == "POST":
        form = OcorrenciaSaudeFuncionarioForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            funcionario.refresh_from_db()

            response = _render_ocorrencias_saude_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "saude"},
                "openHealthTab": {"tab": "ocorrencias"},
            })
            return response
    else:
        form = OcorrenciaSaudeFuncionarioForm(instance=item)

    return render(
        request,
        "rh/funcionarios/modals/modal_ocorrencia_saude_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Editar ocorrência de saúde",
            "modo": "editar",
            "item": item,
        },
    )


def modal_excluir_ocorrencia_saude(request, pk, ocorrencia_id):
    empresa_ativa, redirect_response = _empresa_ativa_or_redirect(
        request,
        "Selecione uma empresa antes de continuar."
    )
    if redirect_response:
        return redirect_response

    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa_ativa)
    item = get_object_or_404(
        OcorrenciaSaudeFuncionario,
        pk=ocorrencia_id,
        funcionario=funcionario
    )

    if request.method == "POST":
        item.delete()
        funcionario.refresh_from_db()

        response = _render_ocorrencias_saude_list(request, funcionario)
        response["HX-Trigger-After-Settle"] = json.dumps({
            "closeSectionModal": True,
            "openSection": {"section": "saude"},
            "openHealthTab": {"tab": "ocorrencias"},
        })
        return response

    return render(
        request,
        "rh/funcionarios/modals/modal_ocorrencia_saude_confirm_delete.html",
        {
            "funcionario": funcionario,
            "item": item,
        },
    )

######################### ANEXOS ##########################################

def _coletar_anexos_sistema(funcionario):
    anexos = []

    for item in funcionario.asos.all():
        if item.anexo:
            anexos.append({
                "titulo": f"ASO {item.get_tipo_display()}",
                "origem": "ASO",
                "data": item.data,
                "arquivo_url": item.anexo.url,
                "arquivo_nome": item.anexo.name.split("/")[-1],
                "section": "saude",
                "health_tab": "aso",
            })

    for item in funcionario.certificados.all():
        if item.anexo:
            anexos.append({
                "titulo": f"Certificado {item.tipo}",
                "origem": "Certificados",
                "data": item.data,
                "arquivo_url": item.anexo.url,
                "arquivo_nome": item.anexo.name.split("/")[-1],
                "section": "saude",
                "health_tab": "certificados",
            })

    for item in funcionario.pcmso_registros.all():
        if item.anexo:
            anexos.append({
                "titulo": "PCMSO",
                "origem": "PCMSO",
                "data": item.data_vencimento,
                "arquivo_url": item.anexo.url,
                "arquivo_nome": item.anexo.name.split("/")[-1],
                "section": "saude",
                "health_tab": "pcmso",
            })

    for item in funcionario.atestados_licencas.all():
        if item.anexo:
            anexos.append({
                "titulo": item.get_tipo_display(),
                "origem": "Atestados / Licenças",
                "data": item.data,
                "arquivo_url": item.anexo.url,
                "arquivo_nome": item.anexo.name.split("/")[-1],
                "section": "saude",
                "health_tab": "atestados",
            })

    for item in funcionario.ocorrencias_saude.all():
        if item.anexo:
            anexos.append({
                "titulo": f"Ocorrência {item.get_tipo_display()}",
                "origem": "Ocorrências",
                "data": item.data,
                "arquivo_url": item.anexo.url,
                "arquivo_nome": item.anexo.name.split("/")[-1],
                "section": "saude",
                "health_tab": "ocorrencias",
            })

    # Campos diretos do funcionário, se existirem
    if getattr(funcionario, "anexo_aviso", None):
        anexos.append({
            "titulo": "Anexo do aviso",
            "origem": "Demissão",
            "data": getattr(funcionario, "data_demissao", None),
            "arquivo_url": funcionario.anexo_aviso.url,
            "arquivo_nome": funcionario.anexo_aviso.name.split("/")[-1],
            "section": "demissao",
            "health_tab": None,
        })

    if getattr(funcionario, "rescisao_assinada", None):
        anexos.append({
            "titulo": "Rescisão assinada",
            "origem": "Demissão",
            "data": getattr(funcionario, "data_demissao", None),
            "arquivo_url": funcionario.rescisao_assinada.url,
            "arquivo_nome": funcionario.rescisao_assinada.name.split("/")[-1],
            "section": "demissao",
            "health_tab": None,
        })

    anexos.sort(key=lambda x: (x["data"] is not None, x["data"]), reverse=True)
    return anexos


def _render_anexos_avulsos_list(request, funcionario):
    return render(
        request,
        "rh/funcionarios/includes/partials/anexos_avulsos_lista.html",
        {
            "funcionario": funcionario,
            "anexos_avulsos_list": funcionario.anexos_avulsos.all(),
        },
    )


def secao_anexos_context(funcionario):
    return {
        "anexos_sistema_list": _coletar_anexos_sistema(funcionario),
        "anexos_avulsos_list": funcionario.anexos_avulsos.all(),
    }


def anexos_avulsos_lista(request, pk):
    funcionario, redirect_response = _get_funcionario_empresa(request, pk)
    if redirect_response:
        return redirect_response

    return _render_anexos_avulsos_list(request, funcionario)


def modal_adicionar_anexo_avulso(request, pk):
    funcionario, redirect_response = _get_funcionario_empresa(request, pk)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = AnexoAvulsoFuncionarioForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.funcionario = funcionario
            item.save()
            funcionario.refresh_from_db()

            response = _render_anexos_avulsos_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "anexos"},
            })
            return response
    else:
        form = AnexoAvulsoFuncionarioForm()

    return render(
        request,
        "rh/funcionarios/modals/modal_anexo_avulso_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Adicionar anexo",
            "modo": "criar",
            "item": None,
        },
    )


def modal_editar_anexo_avulso(request, pk, anexo_id):
    funcionario, redirect_response = _get_funcionario_empresa(request, pk)
    if redirect_response:
        return redirect_response

    item = get_object_or_404(AnexoAvulsoFuncionario, pk=anexo_id, funcionario=funcionario)

    if request.method == "POST":
        form = AnexoAvulsoFuncionarioForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            funcionario.refresh_from_db()

            response = _render_anexos_avulsos_list(request, funcionario)
            response["HX-Trigger-After-Settle"] = json.dumps({
                "closeSectionModal": True,
                "openSection": {"section": "anexos"},
            })
            return response
    else:
        form = AnexoAvulsoFuncionarioForm(instance=item)

    return render(
        request,
        "rh/funcionarios/modals/modal_anexo_avulso_form.html",
        {
            "funcionario": funcionario,
            "form": form,
            "titulo_modal": "Editar anexo",
            "modo": "editar",
            "item": item,
        },
    )


def modal_excluir_anexo_avulso(request, pk, anexo_id):
    funcionario, redirect_response = _get_funcionario_empresa(request, pk)
    if redirect_response:
        return redirect_response

    item = get_object_or_404(AnexoAvulsoFuncionario, pk=anexo_id, funcionario=funcionario)

    if request.method == "POST":
        item.delete()
        funcionario.refresh_from_db()

        response = _render_anexos_avulsos_list(request, funcionario)
        response["HX-Trigger-After-Settle"] = json.dumps({
            "closeSectionModal": True,
            "openSection": {"section": "anexos"},
        })
        return response

    return render(
        request,
        "rh/funcionarios/modals/modal_anexo_avulso_confirm_delete.html",
        {
            "funcionario": funcionario,
            "item": item,
        },
    )