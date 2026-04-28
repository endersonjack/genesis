"""Views do módulo financeiro."""
from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import (
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.moeda_fmt import parse_valor_moeda_br
from core.moeda_fmt import format_decimal_br_moeda
from core.urlutils import redirect_empresa, reverse_empresa

from .forms import (
    BoletoPagamentoForm,
    CaixaEditForm,
    CaixaNovoForm,
    CategoriaFinanceiraForm,
    BoletoRascunhoFormSet,
    PagamentoNotaFiscalItemEditFormSet,
    PagamentoNotaFiscalForm,
    PagamentoNotaFiscalItemFormSet,
    PagamentoNotaFiscalPagamentoForm,
    RecebimentoAvulsoEditForm,
    RecebimentoAvulsoForm,
    RecebimentoLiquidacaoForm,
    RecebimentoMedicaoEditForm,
    RecebimentoMedicaoForm,
)
from .models import (
    BoletoPagamento,
    Caixa,
    CategoriaFinanceira,
    MovimentoCaixa,
    PagamentoNotaFiscal,
    PagamentoNotaFiscalItem,
    PagamentoNotaFiscalPagamento,
    RecebimentoAvulso,
    RecebimentoMedicao,
)

ULTIMOS_RECEBIMENTOS_LISTA_LIMITE = 50


def _empresa(request):
    return getattr(request, 'empresa_ativa', None)


def _is_htmx(request) -> bool:
    return str(request.headers.get('HX-Request', '')).lower() == 'true'


def _recebimento_para_linha(recebimento, tipo: str) -> dict:
    movimento = getattr(recebimento, 'movimento', None)
    return {
        'pk': recebimento.pk,
        'tipo': tipo,
        'tipo_label': 'Avulso' if tipo == 'avulso' else 'Medição',
        'data': recebimento.data,
        'data_pagamento': recebimento.data_pagamento,
        'caixa': recebimento.caixa,
        'cliente': recebimento.cliente,
        'medicao': getattr(recebimento, 'medicao_numero', ''),
        'nf': getattr(recebimento, 'nota_fiscal_numero', ''),
        'obra': getattr(recebimento, 'obra', None),
        'valor': recebimento.valor,
        'impostos': recebimento.impostos,
        'valor_liquido': recebimento.valor_liquido,
        'descricao': recebimento.descricao,
        'status': recebimento.status,
        'movimento': movimento,
    }


def _totais_recebimentos(recebimentos: list[dict]) -> dict:
    return {
        'valor': sum((r['valor'] for r in recebimentos), Decimal('0')),
        'impostos': sum((r['impostos'] for r in recebimentos), Decimal('0')),
        'valor_liquido': sum((r['valor_liquido'] for r in recebimentos), Decimal('0')),
    }


def _criar_movimento_recebimento(recebimento, categoria_origem, data_liquidacao=None):
    data_liquidacao = data_liquidacao or timezone.localdate()
    mov = MovimentoCaixa(
        empresa=recebimento.empresa,
        caixa=recebimento.caixa,
        natureza=MovimentoCaixa.Natureza.ENTRADA,
        categoria_origem=categoria_origem,
        valor=recebimento.valor_liquido,
        data=data_liquidacao,
        descricao=recebimento.descricao,
        observacao=recebimento.observacao,
    )
    mov.full_clean()
    mov.save()
    recebimento.movimento = mov
    recebimento.status = recebimento.Status.PAGO
    recebimento.data_pagamento = mov.data
    recebimento.save(
        update_fields=(
            'movimento',
            'status',
            'data_pagamento',
            'valor',
            'impostos',
            'valor_liquido',
            'atualizado_em',
        )
    )
    return mov


def _aplicar_situacao_boleto(boleto: BoletoPagamento, hoje=None) -> BoletoPagamento:
    hoje = hoje or timezone.localdate()
    if boleto.status == BoletoPagamento.Status.PAGO:
        boleto.situacao_label = 'Pago'
        boleto.situacao_badge_class = 'text-bg-success'
    elif boleto.status == BoletoPagamento.Status.CANCELADO:
        boleto.situacao_label = 'Cancelado'
        boleto.situacao_badge_class = 'text-bg-dark'
    elif boleto.vencimento < hoje:
        boleto.situacao_label = 'Vencido'
        boleto.situacao_badge_class = 'text-bg-danger'
    elif boleto.vencimento == hoje:
        boleto.situacao_label = 'Vence Hoje'
        boleto.situacao_badge_class = 'text-bg-warning'
    else:
        boleto.situacao_label = 'À vencer'
        boleto.situacao_badge_class = 'text-bg-secondary'
    return boleto


def _resumo_pagamento_nf(pagamento, boletos, total_itens: Decimal, hoje=None) -> dict:
    hoje = hoje or timezone.localdate()
    total_pago = Decimal('0')
    valor_em_aberto = total_itens
    pagamento_label = 'Sem pagamento'
    situacao_label = 'Sem pagamento'
    situacao_badge_class = 'text-bg-secondary'

    if not pagamento:
        return {
            'pagamento_label': pagamento_label,
            'situacao_label': situacao_label,
            'situacao_badge_class': situacao_badge_class,
            'valor_pago': total_pago,
            'valor_em_aberto': valor_em_aberto,
        }

    if pagamento.tipo == PagamentoNotaFiscalPagamento.TipoPagamento.BOLETOS:
        total_boletos = sum((boleto.valor for boleto in boletos), Decimal('0'))
        total_pago = sum((boleto.valor_pago or Decimal('0') for boleto in boletos), Decimal('0'))
        valor_em_aberto = max(total_boletos - total_pago, Decimal('0'))
        parcelas = len(boletos)
        pagamento_label = f'Boletos ({parcelas} parcela{"s" if parcelas != 1 else ""})'
        boletos_validos = [
            boleto for boleto in boletos
            if boleto.status != BoletoPagamento.Status.CANCELADO
        ]
        boletos_pagos = [
            boleto for boleto in boletos_validos
            if boleto.status == BoletoPagamento.Status.PAGO
        ]
        boletos_abertos = [
            boleto for boleto in boletos_validos
            if boleto.status != BoletoPagamento.Status.PAGO
        ]
        if boletos_validos and len(boletos_pagos) == len(boletos_validos):
            situacao_label = 'Pago'
            situacao_badge_class = 'text-bg-success'
        elif boletos_pagos:
            situacao_label = 'Parcial'
            situacao_badge_class = 'text-bg-primary'
        elif any(boleto.vencimento < hoje for boleto in boletos_abertos):
            situacao_label = 'Vencido'
            situacao_badge_class = 'text-bg-danger'
        else:
            situacao_label = 'Em aberto'
            situacao_badge_class = 'text-bg-warning'
    else:
        pagamento_label = pagamento.get_tipo_display()
        total_pago = pagamento.total_a_pagar()
        valor_em_aberto = Decimal('0')
        situacao_label = 'Pago'
        situacao_badge_class = 'text-bg-success'

    return {
        'pagamento_label': pagamento_label,
        'situacao_label': situacao_label,
        'situacao_badge_class': situacao_badge_class,
        'valor_pago': total_pago,
        'valor_em_aberto': valor_em_aberto,
    }


def _annotate_saldo(qs):
    dec = DecimalField(max_digits=16, decimal_places=2)
    return (
        qs.order_by('tipo', 'nome')
        .annotate(
            _entradas=Coalesce(
                Sum(
                    'movimentos__valor',
                    filter=Q(movimentos__natureza='entrada'),
                ),
                Value(Decimal('0')),
                output_field=dec,
            ),
            _saidas=Coalesce(
                Sum(
                    'movimentos__valor',
                    filter=Q(movimentos__natureza='saida'),
                ),
                Value(Decimal('0')),
                output_field=dec,
            ),
        )
        .annotate(
            saldo=ExpressionWrapper(
                F('_entradas') - F('_saidas'),
                output_field=dec,
            ),
        )
    )


def _caixas_com_saldo(empresa, *, somente_ativos: bool = True):
    qs = Caixa.objects.filter(empresa=empresa)
    if somente_ativos:
        qs = qs.filter(ativo=True)
    return _annotate_saldo(qs)


@login_required
def dashboard(request):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')
    return render(
        request,
        'financeiro/dashboard.html',
        {'page_title': 'Financeiro'},
    )


@login_required
def relatorios(request):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')

    hoje = timezone.localdate()
    dec = DecimalField(max_digits=16, decimal_places=2)
    caixas = list(_caixas_com_saldo(empresa, somente_ativos=True))
    saldo_consolidado = sum((caixa.saldo for caixa in caixas), Decimal('0'))

    recebimentos_abertos_av = RecebimentoAvulso.objects.filter(
        empresa=empresa,
        status=RecebimentoAvulso.Status.ABERTO,
    ).aggregate(
        valor=Coalesce(Sum('valor'), Value(Decimal('0')), output_field=dec),
        impostos=Coalesce(Sum('impostos'), Value(Decimal('0')), output_field=dec),
        liquido=Coalesce(Sum('valor_liquido'), Value(Decimal('0')), output_field=dec),
    )
    recebimentos_abertos_med = RecebimentoMedicao.objects.filter(
        empresa=empresa,
        status=RecebimentoMedicao.Status.ABERTO,
    ).aggregate(
        valor=Coalesce(Sum('valor'), Value(Decimal('0')), output_field=dec),
        impostos=Coalesce(Sum('impostos'), Value(Decimal('0')), output_field=dec),
        liquido=Coalesce(Sum('valor_liquido'), Value(Decimal('0')), output_field=dec),
    )
    recebimentos_pagos_av = RecebimentoAvulso.objects.filter(
        empresa=empresa,
        status=RecebimentoAvulso.Status.PAGO,
    ).aggregate(
        valor=Coalesce(Sum('valor'), Value(Decimal('0')), output_field=dec),
        impostos=Coalesce(Sum('impostos'), Value(Decimal('0')), output_field=dec),
        liquido=Coalesce(Sum('valor_liquido'), Value(Decimal('0')), output_field=dec),
    )
    recebimentos_pagos_med = RecebimentoMedicao.objects.filter(
        empresa=empresa,
        status=RecebimentoMedicao.Status.PAGO,
    ).aggregate(
        valor=Coalesce(Sum('valor'), Value(Decimal('0')), output_field=dec),
        impostos=Coalesce(Sum('impostos'), Value(Decimal('0')), output_field=dec),
        liquido=Coalesce(Sum('valor_liquido'), Value(Decimal('0')), output_field=dec),
    )

    boletos_abertos_status = (
        BoletoPagamento.Status.RASCUNHO,
        BoletoPagamento.Status.EMITIDO,
    )
    boletos_vencidos = BoletoPagamento.objects.filter(
        pagamento_nf__empresa=empresa,
        vencimento__lt=hoje,
        status__in=boletos_abertos_status,
    ).aggregate(
        total=Coalesce(Sum('valor'), Value(Decimal('0')), output_field=dec),
    )
    boletos_a_vencer = BoletoPagamento.objects.filter(
        pagamento_nf__empresa=empresa,
        vencimento__gte=hoje,
        status__in=boletos_abertos_status,
    ).aggregate(
        total=Coalesce(Sum('valor'), Value(Decimal('0')), output_field=dec),
    )
    notas_sem_pagamento = list(
        PagamentoNotaFiscal.objects.filter(
            empresa=empresa,
            pagamento__isnull=True,
        )
        .select_related('fornecedor')
        .prefetch_related('itens')
    )
    total_notas_sem_pagamento = sum(
        (nf.total_itens() for nf in notas_sem_pagamento),
        Decimal('0'),
    )

    def somar_agregados(a, b):
        return {
            'valor': a['valor'] + b['valor'],
            'impostos': a['impostos'] + b['impostos'],
            'liquido': a['liquido'] + b['liquido'],
        }

    return render(
        request,
        'financeiro/relatorios.html',
        {
            'page_title': 'Relatórios Financeiros',
            'saldo_consolidado': saldo_consolidado,
            'total_caixas_ativos': len(caixas),
            'recebimentos_abertos': somar_agregados(
                recebimentos_abertos_av,
                recebimentos_abertos_med,
            ),
            'recebimentos_pagos': somar_agregados(
                recebimentos_pagos_av,
                recebimentos_pagos_med,
            ),
            'boletos_vencidos_total': boletos_vencidos['total'],
            'boletos_a_vencer_total': boletos_a_vencer['total'],
            'notas_sem_pagamento_total': total_notas_sem_pagamento,
            'notas_sem_pagamento_qtd': len(notas_sem_pagamento),
        },
    )


@login_required
def buscar_pagamentos(request):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')

    query = str(request.GET.get('q', '')).strip()
    fornecedor = str(request.GET.get('fornecedor', '')).strip()
    valor_raw = str(request.GET.get('valor', '')).strip()
    data_inicio = str(request.GET.get('data_inicio', '')).strip()
    data_fim = str(request.GET.get('data_fim', '')).strip()
    status_vencido_raw = str(request.GET.get('status_vencido', '')).strip()
    status_aberto_raw = str(request.GET.get('status_aberto', '')).strip()
    status_pago_raw = str(request.GET.get('status_pago', '')).strip()
    tem_status_expresso = (
        'status_vencido' in request.GET
        or 'status_aberto' in request.GET
        or 'status_pago' in request.GET
    )
    status_vencido = (
        status_vencido_raw in ('1', 'on', 'true')
        if tem_status_expresso
        else True
    )
    status_aberto = status_aberto_raw in ('1', 'on', 'true')
    status_pago = status_pago_raw in ('1', 'on', 'true')
    resultados = []
    erro_valor = ''
    filtros_ativos = any(
        [
            query,
            fornecedor,
            valor_raw,
            data_inicio,
            data_fim,
            status_vencido,
            status_aberto,
            status_pago,
        ]
    )

    if filtros_ativos:
        hoje = timezone.localdate()
        valor = None
        if valor_raw:
            try:
                valor = parse_valor_moeda_br(valor_raw)
            except Exception:
                erro_valor = 'Informe um valor válido no padrão 0,00.'

        nfs_qs = (
            PagamentoNotaFiscal.objects.filter(empresa=empresa)
            .select_related('fornecedor', 'caixa', 'pagamento')
            .prefetch_related('boletos')
            .annotate(
                total_itens_calc=Coalesce(
                    Sum('itens__valor_total'),
                    Value(Decimal('0')),
                    output_field=DecimalField(max_digits=16, decimal_places=2),
                )
            )
            .order_by('-data_emissao', '-pk')
        )
        if fornecedor:
            nfs_qs = nfs_qs.filter(fornecedor__nome__icontains=fornecedor)
        if data_inicio:
            nfs_qs = nfs_qs.filter(data_emissao__gte=data_inicio)
        if data_fim:
            nfs_qs = nfs_qs.filter(data_emissao__lte=data_fim)
        if query:
            nfs_qs = nfs_qs.filter(
                Q(numero_nf__icontains=query) | Q(boletos__numero_doc__icontains=query)
            )
        if status_vencido or status_aberto or status_pago:
            status_filter = Q()
            if status_vencido:
                status_filter |= Q(
                    pagamento__tipo=PagamentoNotaFiscalPagamento.TipoPagamento.BOLETOS,
                    boletos__status__in=[
                        BoletoPagamento.Status.RASCUNHO,
                        BoletoPagamento.Status.EMITIDO,
                    ],
                    boletos__vencimento__lt=hoje,
                )
            if status_aberto:
                status_filter |= (
                    Q(pagamento__isnull=True)
                    | Q(
                        pagamento__tipo=PagamentoNotaFiscalPagamento.TipoPagamento.BOLETOS,
                        boletos__status__in=[
                            BoletoPagamento.Status.RASCUNHO,
                            BoletoPagamento.Status.EMITIDO,
                        ],
                    )
                )
            if status_pago:
                status_filter |= (
                    Q(
                        pagamento__tipo__in=[
                            PagamentoNotaFiscalPagamento.TipoPagamento.AVISTA,
                            PagamentoNotaFiscalPagamento.TipoPagamento.CREDITO,
                        ]
                    )
                    | Q(
                        pagamento__tipo=PagamentoNotaFiscalPagamento.TipoPagamento.BOLETOS,
                        boletos__status=BoletoPagamento.Status.PAGO,
                    )
                )
            nfs_qs = nfs_qs.filter(status_filter)
        if valor_raw and not erro_valor:
            if valor is None:
                resultados = []
                nfs_qs = PagamentoNotaFiscal.objects.none()
            else:
                nfs_qs = nfs_qs.filter(
                    Q(total_itens_calc=valor) | Q(boletos__valor=valor)
                )

        for nf in nfs_qs.distinct():
            origens = set()
            boletos_all = list(nf.boletos.all().order_by('vencimento', 'parcela', 'pk'))
            boletos_relacionados = list(boletos_all)
            boletos_vencidos = [
                boleto for boleto in boletos_all
                if (
                    boleto.status
                    in (BoletoPagamento.Status.RASCUNHO, BoletoPagamento.Status.EMITIDO)
                    and boleto.vencimento < hoje
                )
            ]
            status_labels = []
            pg = getattr(nf, 'pagamento', None)
            tem_boleto_aberto = any(
                boleto.status in (BoletoPagamento.Status.RASCUNHO, BoletoPagamento.Status.EMITIDO)
                for boleto in boletos_all
            )
            tem_boleto_pago = any(
                boleto.status == BoletoPagamento.Status.PAGO for boleto in boletos_all
            )
            if pg is None:
                status_labels.append('Sem pagamento')
            elif pg.tipo in (
                PagamentoNotaFiscalPagamento.TipoPagamento.AVISTA,
                PagamentoNotaFiscalPagamento.TipoPagamento.CREDITO,
            ):
                status_labels.append('Pago')
            else:
                if tem_boleto_aberto:
                    status_labels.append('Em aberto')
                if tem_boleto_pago:
                    status_labels.append('Pago')
            if query:
                if query.lower() in (nf.numero_nf or '').lower():
                    origens.add('nota_fiscal')
                boletos_relacionados = [
                    boleto for boleto in boletos_relacionados
                    if query.lower() in (boleto.numero_doc or '').lower()
                ]
                if boletos_relacionados:
                    origens.add('numero_doc')
            elif status_vencido and not status_aberto and not status_pago:
                boletos_relacionados = boletos_vencidos
            if valor_raw and not erro_valor and valor is not None:
                if nf.total_itens_calc == valor:
                    origens.add('valor_nf')
                boletos_por_valor = [
                    boleto for boleto in nf.boletos.all().order_by('vencimento', 'parcela', 'pk')
                    if boleto.valor == valor
                ]
                if boletos_por_valor:
                    origens.add('valor_doc')
                    if not query:
                        boletos_relacionados = boletos_por_valor
            resultados.append(
                {
                    'nf': nf,
                    'tipo_pagamento_label': pg.get_tipo_display() if pg else 'Sem pagamento',
                    'origens': origens,
                    'boletos_relacionados': boletos_relacionados,
                    'boletos_vencidos': boletos_vencidos,
                    'vencimento_mais_antigo': boletos_vencidos[0].vencimento
                    if boletos_vencidos
                    else None,
                    'total_boletos_relacionados': sum(
                        (boleto.valor for boleto in boletos_relacionados),
                        Decimal('0'),
                    ),
                    'total_itens': nf.total_itens_calc,
                    'status_labels': status_labels,
                }
            )

    return render(
        request,
        'financeiro/busca_pagamentos.html',
        {
            'page_title': 'Buscar Pagamentos',
            'query': query,
            'fornecedor': fornecedor,
            'valor': valor_raw,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'status_vencido': status_vencido,
            'status_aberto': status_aberto,
            'status_pago': status_pago,
            'erro_valor': erro_valor,
            'filtros_ativos': filtros_ativos,
            'resultados': resultados,
        },
    )


@login_required
def partial_dashboard_cards(request):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')
    if not _is_htmx(request):
        return redirect_empresa(request, 'financeiro:dashboard')

    hoje = timezone.localdate()
    boleto_status_aberto = (
        BoletoPagamento.Status.RASCUNHO,
        BoletoPagamento.Status.EMITIDO,
    )
    boletos_venc_hoje = list(
        BoletoPagamento.objects.filter(
            pagamento_nf__empresa=empresa,
            vencimento=hoje,
            status__in=boleto_status_aberto,
        )
        .select_related('pagamento_nf', 'pagamento_nf__fornecedor')
        .order_by('vencimento', 'parcela', 'pk')[:50]
    )
    boletos_vencidos = list(
        BoletoPagamento.objects.filter(
            pagamento_nf__empresa=empresa,
            vencimento__lt=hoje,
            status__in=boleto_status_aberto,
        )
        .select_related('pagamento_nf', 'pagamento_nf__fornecedor')
        .order_by('vencimento', 'parcela', 'pk')[:100]
    )
    notas_sem_pagamento = list(
        PagamentoNotaFiscal.objects.filter(
            empresa=empresa,
            data_emissao__lte=hoje,
            pagamento__isnull=True,
        )
        .select_related('fornecedor', 'caixa')
        .order_by('-data_emissao', '-pk')[:50]
    )
    total_boletos_venc_hoje = sum((b.valor for b in boletos_venc_hoje), Decimal('0'))
    total_boletos_vencidos = sum((b.valor for b in boletos_vencidos), Decimal('0'))
    total_notas_sem_pagamento = sum((nf.total_itens() for nf in notas_sem_pagamento), Decimal('0'))
    total_em_aberto_sem_pagamento = total_boletos_vencidos + total_notas_sem_pagamento
    ultimos_lancamentos = list(
        MovimentoCaixa.objects.filter(empresa=empresa)
        .select_related('caixa')
        .order_by('-data', '-pk')[:10]
    )

    # Feed unificado (últimas movimentações): entradas/saídas + NFs (com/sem pagamento)
    nf_qs = (
        PagamentoNotaFiscal.objects.filter(empresa=empresa)
        .select_related('fornecedor', 'caixa', 'pagamento')
        .annotate(
            total_itens=Coalesce(
                Sum('itens__valor_total'),
                Value(Decimal('0')),
                output_field=DecimalField(max_digits=16, decimal_places=2),
            )
        )
        .order_by('-criado_em', '-pk')[:25]
    )
    eventos = []
    for m in MovimentoCaixa.objects.filter(empresa=empresa).select_related('caixa').order_by(
        '-criado_em', '-pk'
    )[:25]:
        eventos.append(
            {
                'kind': 'movimento',
                'sort_dt': m.criado_em,
                'mov_pk': m.pk,
                'data': m.data,
                'caixa_nome': m.caixa.nome if m.caixa_id else '—',
                'caixa_pk': m.caixa_id,
                'descricao': m.descricao,
                'valor': m.valor,
                'valor_sinal': '+' if m.natureza == MovimentoCaixa.Natureza.ENTRADA else '-',
                'badge_text': 'Entrada' if m.natureza == MovimentoCaixa.Natureza.ENTRADA else 'Saída',
                'badge_class': 'text-bg-success'
                if m.natureza == MovimentoCaixa.Natureza.ENTRADA
                else 'text-bg-danger',
            }
        )
    for nf in nf_qs:
        pg = getattr(nf, 'pagamento', None)
        if pg and pg.tipo == PagamentoNotaFiscalPagamento.TipoPagamento.BOLETOS:
            badge_text = 'Boleto'
            badge_class = 'text-bg-danger'
        elif pg and pg.tipo == PagamentoNotaFiscalPagamento.TipoPagamento.AVISTA:
            badge_text = 'À vista'
            badge_class = 'text-bg-danger'
        elif pg and pg.tipo == PagamentoNotaFiscalPagamento.TipoPagamento.CREDITO:
            badge_text = 'Crédito'
            badge_class = 'text-bg-danger'
        else:
            badge_text = 'Sem pagamento'
            badge_class = 'text-bg-secondary'

        eventos.append(
            {
                'kind': 'nf',
                'sort_dt': nf.criado_em,
                'data': nf.data_emissao,
                'caixa_nome': nf.caixa.nome if nf.caixa_id else '—',
                'descricao': f'{nf.fornecedor.nome} — NF {nf.numero_nf}',
                'valor': nf.total_itens,
                'valor_sinal': '-',
                'badge_text': badge_text,
                'badge_class': badge_class,
                'nf_pk': nf.pk,
            }
        )
    eventos.sort(key=lambda e: (e['sort_dt'] or hoje), reverse=True)
    eventos = eventos[:10]

    return render(
        request,
        'financeiro/partials/dashboard_cards_loaded.html',
        {
            'hoje': hoje,
            'boletos_venc_hoje': boletos_venc_hoje,
            'total_boletos_venc_hoje': total_boletos_venc_hoje,
            'boletos_vencidos': boletos_vencidos,
            'notas_sem_pagamento': notas_sem_pagamento,
            'total_em_aberto_sem_pagamento': total_em_aberto_sem_pagamento,
            'ultimos_lancamentos': ultimos_lancamentos,
            'ultimos_eventos': eventos,
        },
    )


@login_required
def caixa_lista(request):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')

    caixas = list(_caixas_com_saldo(empresa, somente_ativos=False))
    ativos = [c for c in caixas if c.ativo]
    saldo_consolidado = sum((c.saldo for c in ativos), Decimal('0'))
    caixa_padrao = next((c for c in caixas if c.tipo == Caixa.Tipo.GERAL), None)

    return render(
        request,
        'financeiro/caixa_lista.html',
        {
            'page_title': 'Caixas',
            'caixas': caixas,
            'saldo_consolidado': saldo_consolidado,
            'caixa_padrao': caixa_padrao,
        },
    )


@login_required
def caixa_novo(request):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')

    form = CaixaNovoForm(request.POST or None, empresa=empresa)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Subcaixa criada.')
        return redirect_empresa(request, 'financeiro:caixa_lista')

    return render(
        request,
        'financeiro/caixa_form.html',
        {
            'page_title': 'Nova subcaixa',
            'form': form,
            'modo': 'novo',
        },
    )


@login_required
def caixa_detalhe(request, pk):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')

    caixa = get_object_or_404(Caixa.objects.filter(empresa=empresa), pk=pk)

    movs_chron = list(caixa.movimentos.order_by('data', 'pk'))
    acum = Decimal('0')
    saldo_apos = {}
    for m in movs_chron:
        if m.natureza == MovimentoCaixa.Natureza.ENTRADA:
            acum += m.valor
        else:
            acum -= m.valor
        saldo_apos[m.pk] = acum

    movimentos = list(
        caixa.movimentos.order_by('-data', '-pk').select_related(
            'recebimento_avulso',
            'recebimento_avulso__cliente',
            'recebimento_medicao',
            'recebimento_medicao__cliente',
            'recebimento_medicao__obra',
        )
    )
    for m in movimentos:
        # Nome sem "_" inicial: o motor de templates Django não expõe atributos que começam com _.
        m.saldo_apos_lancamento = saldo_apos.get(m.pk, Decimal('0'))

    return render(
        request,
        'financeiro/caixa_detalhe.html',
        {
            'page_title': caixa.nome,
            'caixa': caixa,
            'movimentos': movimentos,
            'saldo_atual': caixa.saldo_atual(),
        },
    )


@login_required
def caixa_editar(request, pk):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')

    caixa = get_object_or_404(Caixa.objects.filter(empresa=empresa), pk=pk)
    form = CaixaEditForm(
        request.POST or None,
        instance=caixa,
        empresa=empresa,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Caixa atualizado.')
        return redirect_empresa(request, 'financeiro:caixa_detalhe', kwargs={'pk': caixa.pk})

    return render(
        request,
        'financeiro/caixa_form.html',
        {
            'page_title': f'Editar — {caixa.nome}',
            'form': form,
            'caixa': caixa,
            'modo': 'editar',
        },
    )


@login_required
def caixa_inativar(request, pk):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')
    if request.method != 'POST':
        return redirect_empresa(request, 'financeiro:caixa_detalhe', kwargs={'pk': pk})

    caixa = get_object_or_404(Caixa.objects.filter(empresa=empresa), pk=pk)
    caixa.ativo = False
    caixa.save()
    messages.success(request, 'Caixa inativado. O histórico de movimentos foi preservado.')
    return redirect_empresa(request, 'financeiro:caixa_lista')


@login_required
def caixa_reativar(request, pk):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')
    if request.method != 'POST':
        return redirect_empresa(request, 'financeiro:caixa_detalhe', kwargs={'pk': pk})

    caixa = get_object_or_404(Caixa.objects.filter(empresa=empresa), pk=pk)
    caixa.ativo = True
    caixa.save()
    messages.success(request, 'Caixa reativado.')
    return redirect_empresa(request, 'financeiro:caixa_detalhe', kwargs={'pk': caixa.pk})


@login_required
def movimentar_caixa(request):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')
    recebimentos_avulsos = (
        RecebimentoAvulso.objects.filter(empresa=empresa)
        .select_related('caixa', 'cliente', 'movimento')
        .order_by('-data', '-pk')
    )
    recebimentos_medicao = (
        RecebimentoMedicao.objects.filter(empresa=empresa)
        .select_related('caixa', 'cliente', 'obra', 'movimento')
        .order_by('-data', '-pk')
    )
    recebimentos = [
        *(_recebimento_para_linha(r, 'avulso') for r in recebimentos_avulsos),
        *(_recebimento_para_linha(r, 'medicao') for r in recebimentos_medicao),
    ]
    recebimentos.sort(key=lambda r: (r['data'] or timezone.localdate(), r['pk']), reverse=True)
    recebimentos_abertos = [
        r for r in recebimentos
        if r['status'] in (RecebimentoAvulso.Status.ABERTO, RecebimentoMedicao.Status.ABERTO)
    ]
    recebimentos_pagos = [
        r for r in recebimentos
        if r['status'] in (RecebimentoAvulso.Status.PAGO, RecebimentoMedicao.Status.PAGO)
    ][:ULTIMOS_RECEBIMENTOS_LISTA_LIMITE]
    return render(
        request,
        'financeiro/movimentar_caixa.html',
        {
            'page_title': 'Recebimentos',
            'recebimentos_abertos': recebimentos_abertos,
            'recebimentos_pagos': recebimentos_pagos,
            'totais_abertos': _totais_recebimentos(recebimentos_abertos),
            'totais_pagos': _totais_recebimentos(recebimentos_pagos),
        },
    )


@login_required
def recebimento_liquidar(request, tipo: str, pk: int):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')

    if tipo == 'avulso':
        recebimento = get_object_or_404(
            RecebimentoAvulso.objects.filter(empresa=empresa).select_related('caixa'),
            pk=pk,
        )
        categoria_origem = MovimentoCaixa.CategoriaOrigem.RECEBIMENTO_AVULSO
    elif tipo == 'medicao':
        recebimento = get_object_or_404(
            RecebimentoMedicao.objects.filter(empresa=empresa).select_related('caixa'),
            pk=pk,
        )
        categoria_origem = MovimentoCaixa.CategoriaOrigem.RECEBIMENTO_MEDICAO
    else:
        messages.error(request, 'Tipo de recebimento inválido.')
        return redirect_empresa(request, 'financeiro:movimentar_caixa')

    if recebimento.status == recebimento.Status.PAGO:
        messages.info(request, 'Este recebimento já está liquidado.')
        return redirect_empresa(request, 'financeiro:movimentar_caixa')
    if not recebimento.caixa_id:
        messages.error(request, 'Informe um caixa antes de liquidar este recebimento.')
        return redirect_empresa(request, 'financeiro:movimentar_caixa')

    form = RecebimentoLiquidacaoForm(
        request.POST or None,
        recebimento=recebimento,
    )
    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        recebimento.valor = cd['valor']
        recebimento.impostos = cd['impostos']
        recebimento.valor_liquido = cd['valor_liquido']
        with transaction.atomic():
            _criar_movimento_recebimento(
                recebimento,
                categoria_origem,
                data_liquidacao=cd['data_pagamento'],
            )

        messages.success(request, 'Recebimento liquidado e lançado no caixa.')
        if _is_htmx(request):
            response = HttpResponse(status=200)
            response['HX-Redirect'] = reverse_empresa(request, 'financeiro:movimentar_caixa')
            return response
        return redirect_empresa(request, 'financeiro:movimentar_caixa')

    if _is_htmx(request):
        return render(
            request,
            'financeiro/partials/recebimento_liquidar_modal.html',
            {
                'page_title': 'Liquidar recebimento',
                'form': form,
                'recebimento': recebimento,
                'tipo': tipo,
                'post_url': reverse_empresa(
                    request,
                    'financeiro:recebimento_liquidar',
                    kwargs={'tipo': tipo, 'pk': recebimento.pk},
                ),
            },
        )
    return redirect_empresa(request, 'financeiro:movimentar_caixa')


@login_required
def recebimento_editar(request, tipo: str, pk: int):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')

    if tipo == 'avulso':
        recebimento = get_object_or_404(
            RecebimentoAvulso.objects.filter(empresa=empresa).select_related('caixa', 'movimento'),
            pk=pk,
        )
        form_class = RecebimentoAvulsoEditForm
    elif tipo == 'medicao':
        recebimento = get_object_or_404(
            RecebimentoMedicao.objects.filter(empresa=empresa).select_related(
                'caixa',
                'movimento',
                'obra',
            ),
            pk=pk,
        )
        form_class = RecebimentoMedicaoEditForm
    else:
        messages.error(request, 'Tipo de recebimento inválido.')
        return redirect_empresa(request, 'financeiro:movimentar_caixa')

    if request.method == 'POST' and request.POST.get('action') == 'excluir':
        with transaction.atomic():
            movimento = getattr(recebimento, 'movimento', None)
            recebimento.delete()
            if movimento:
                movimento.delete()
        messages.success(request, 'Recebimento excluído.')
        if _is_htmx(request):
            response = HttpResponse(status=200)
            response['HX-Redirect'] = reverse_empresa(request, 'financeiro:movimentar_caixa')
            return response
        return redirect_empresa(request, 'financeiro:movimentar_caixa')

    form = form_class(
        request.POST or None,
        request.FILES or None,
        empresa=empresa,
        instance=recebimento,
    )
    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        with transaction.atomic():
            recebimento.caixa = cd['caixa']
            recebimento.cliente = cd['cliente']
            recebimento.categoria = cd.get('categoria')
            recebimento.data = cd['data']
            recebimento.data_pagamento = cd.get('data_pagamento')
            recebimento.valor = cd['valor']
            recebimento.impostos = cd['impostos']
            recebimento.valor_liquido = cd['valor_liquido']
            recebimento.descricao = cd['descricao']
            recebimento.observacao = cd.get('observacao') or ''
            if cd.get('comprovante'):
                recebimento.comprovante = cd['comprovante']
            if tipo == 'medicao':
                recebimento.obra = cd['obra']
                recebimento.medicao_numero = cd['medicao_numero']
                recebimento.nota_fiscal_numero = (cd.get('nota_fiscal_numero') or '').strip()
            recebimento.full_clean()
            recebimento.save()

            movimento = getattr(recebimento, 'movimento', None)
            if movimento:
                movimento.caixa = recebimento.caixa
                movimento.valor = recebimento.valor_liquido
                movimento.data = recebimento.data_pagamento or recebimento.data
                movimento.descricao = recebimento.descricao
                movimento.observacao = recebimento.observacao
                movimento.full_clean()
                movimento.save()

        messages.success(request, 'Recebimento atualizado.')
        if _is_htmx(request):
            response = HttpResponse(status=200)
            response['HX-Redirect'] = reverse_empresa(request, 'financeiro:movimentar_caixa')
            return response
        return redirect_empresa(request, 'financeiro:movimentar_caixa')

    if _is_htmx(request):
        return render(
            request,
            'financeiro/partials/recebimento_editar_modal.html',
            {
                'page_title': 'Editar recebimento',
                'form': form,
                'recebimento': recebimento,
                'tipo': tipo,
                'post_url': reverse_empresa(
                    request,
                    'financeiro:recebimento_editar',
                    kwargs={'tipo': tipo, 'pk': recebimento.pk},
                ),
            },
        )
    return redirect_empresa(request, 'financeiro:movimentar_caixa')


@login_required
def movimentar_pagamento(request):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')
    return render(
        request,
        'financeiro/movimentar_pagamento.html',
        {'page_title': 'Pagamentos'},
    )


@login_required
def recebimento_avulso_novo(request):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')

    form = RecebimentoAvulsoForm(
        request.POST or None,
        request.FILES or None,
        empresa=empresa,
    )
    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        with transaction.atomic():
            extra = {
                'empresa': empresa,
                'caixa': cd['caixa'],
                'cliente': cd['cliente'],
                'categoria': cd.get('categoria'),
                'status': RecebimentoAvulso.Status.ABERTO,
                'data': cd['data'],
                'valor': cd['valor'],
                'impostos': cd['impostos'],
                'valor_liquido': cd['valor_liquido'],
                'descricao': cd['descricao'],
                'observacao': cd.get('observacao') or '',
            }
            if cd.get('comprovante'):
                extra['comprovante'] = cd['comprovante']
            RecebimentoAvulso.objects.create(**extra)
        messages.success(request, 'Recebimento avulso registrado em aberto.')
        if _is_htmx(request):
            response = HttpResponse(status=200)
            response['HX-Redirect'] = reverse_empresa(request, 'financeiro:movimentar_caixa')
            return response
        return redirect_empresa(request, 'financeiro:movimentar_caixa')

    if _is_htmx(request):
        return render(
            request,
            'financeiro/partials/recebimento_form_modal.html',
            {
                'page_title': 'Recebimento avulso',
                'modal_title': 'Lançar recebimento avulso',
                'modal_subtitle': 'O recebimento será registrado em aberto até a liquidação.',
                'form': form,
                'post_url': reverse_empresa(request, 'financeiro:recebimento_avulso_novo'),
            },
        )

    return render(
        request,
        'financeiro/recebimento_avulso_form.html',
        {
            'page_title': 'Recebimento avulso',
            'form': form,
            'post_url': reverse_empresa(request, 'financeiro:recebimento_avulso_novo'),
        },
    )


@login_required
def recebimento_medicao_novo(request):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')

    form = RecebimentoMedicaoForm(
        request.POST or None,
        request.FILES or None,
        empresa=empresa,
    )
    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        desc_extra = f' — Obra: {cd["obra"].nome} — Medição nº {cd["medicao_numero"]}'
        base = cd['descricao']
        max_base = 500 - len(desc_extra)
        if max_base >= 1:
            descricao = (base[:max_base].rstrip() + desc_extra)[:500]
        else:
            descricao = desc_extra[:500]
        with transaction.atomic():
            extra_m = {
                'empresa': empresa,
                'caixa': cd['caixa'],
                'cliente': cd['cliente'],
                'categoria': cd.get('categoria'),
                'obra': cd['obra'],
                'status': RecebimentoMedicao.Status.ABERTO,
                'data': cd['data'],
                'valor': cd['valor'],
                'impostos': cd['impostos'],
                'valor_liquido': cd['valor_liquido'],
                'descricao': descricao[:500],
                'observacao': cd.get('observacao') or '',
                'medicao_numero': cd['medicao_numero'],
                'nota_fiscal_numero': (cd.get('nota_fiscal_numero') or '').strip(),
            }
            if cd.get('comprovante'):
                extra_m['comprovante'] = cd['comprovante']
            RecebimentoMedicao.objects.create(**extra_m)
        messages.success(request, 'Recebimento por medição registrado em aberto.')
        if _is_htmx(request):
            response = HttpResponse(status=200)
            response['HX-Redirect'] = reverse_empresa(request, 'financeiro:movimentar_caixa')
            return response
        return redirect_empresa(request, 'financeiro:movimentar_caixa')

    if _is_htmx(request):
        return render(
            request,
            'financeiro/partials/recebimento_form_modal.html',
            {
                'page_title': 'Recebimento por medição',
                'modal_title': 'Lançar recebimento de medição',
                'modal_subtitle': 'O recebimento será registrado em aberto até a liquidação.',
                'form': form,
                'post_url': reverse_empresa(request, 'financeiro:recebimento_medicao_novo'),
            },
        )

    return render(
        request,
        'financeiro/recebimento_medicao_form.html',
        {
            'page_title': 'Recebimento por medição',
            'form': form,
            'post_url': reverse_empresa(request, 'financeiro:recebimento_medicao_novo'),
        },
    )


@login_required
def categoria_lista(request):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')

    categorias = list(
        CategoriaFinanceira.objects.filter(empresa=empresa).order_by('movimentacao_tipo', 'nome')
    )
    return render(
        request,
        'financeiro/categoria_lista.html',
        {
            'page_title': 'Categorias',
            'categorias': categorias,
        },
    )


@login_required
def categoria_novo(request):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')

    form = CategoriaFinanceiraForm(
        request.POST or None,
        empresa=empresa,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Categoria criada.')
        return redirect_empresa(request, 'financeiro:categoria_lista')

    return render(
        request,
        'financeiro/categoria_form.html',
        {
            'page_title': 'Nova categoria',
            'form': form,
            'modo': 'novo',
        },
    )


@login_required
def categoria_editar(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')

    categoria = get_object_or_404(CategoriaFinanceira.objects.filter(empresa=empresa), pk=pk)
    form = CategoriaFinanceiraForm(
        request.POST or None,
        instance=categoria,
        empresa=empresa,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Categoria atualizada.')
        return redirect_empresa(request, 'financeiro:categoria_lista')

    return render(
        request,
        'financeiro/categoria_form.html',
        {
            'page_title': f'Editar — {categoria.nome}',
            'form': form,
            'modo': 'editar',
            'categoria': categoria,
        },
    )


@login_required
def categoria_inativar(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')
    if request.method != 'POST':
        return redirect_empresa(request, 'financeiro:dashboard')

    categoria = get_object_or_404(CategoriaFinanceira.objects.filter(empresa=empresa), pk=pk)
    categoria.ativo = False
    categoria.save()
    messages.success(request, 'Categoria inativada.')
    return redirect_empresa(request, 'financeiro:categoria_lista')


@login_required
def categoria_reativar(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')
    if request.method != 'POST':
        return redirect_empresa(request, 'financeiro:dashboard')

    categoria = get_object_or_404(CategoriaFinanceira.objects.filter(empresa=empresa), pk=pk)
    categoria.ativo = True
    categoria.save()
    messages.success(request, 'Categoria reativada.')
    return redirect_empresa(request, 'financeiro:categoria_lista')


@login_required
def pagamento_nf_novo(request):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')

    form = PagamentoNotaFiscalForm(request.POST or None, empresa=empresa)
    itens_fs = PagamentoNotaFiscalItemFormSet(
        request.POST or None,
        prefix='itens',
        form_kwargs={
            'empresa': empresa,
            'default_caixa_id': form.initial.get('caixa'),
        },
    )
    pagamento_form = PagamentoNotaFiscalPagamentoForm(request.POST or None, prefix='pg')
    boletos_fs = BoletoRascunhoFormSet(request.POST or None, prefix='boletos')
    dup_nf = None
    force_save = str(request.POST.get('force_save', '')).strip() == '1'

    if request.method == 'POST':
        ok = (
            form.is_valid()
            and itens_fs.is_valid()
            and pagamento_form.is_valid()
            and boletos_fs.is_valid()
        )

        if ok:
            cd = form.cleaned_data
            dup_nf = (
                PagamentoNotaFiscal.objects.filter(
                    empresa=empresa,
                    fornecedor=cd['fornecedor'],
                    numero_nf=cd['numero_nf'],
                )
                .order_by('-pk')
                .first()
            )
            if dup_nf and not force_save:
                ok = False

        if ok:
            with transaction.atomic():
                nf = form.save()

                itens_objs = []
                for f in itens_fs:
                    if not getattr(f, 'cleaned_data', None):
                        continue
                    if f.cleaned_data.get('DELETE'):
                        continue
                    if f.cleaned_data.get('_skip_form'):
                        continue
                    item = f.save(commit=False)
                    item.pagamento_nf = nf
                    # Caixa já veio no form; se vazio por algum motivo, default da NF.
                    if not item.caixa_id:
                        item.caixa = nf.caixa
                    item.full_clean()
                    itens_objs.append(item)
                if not itens_objs:
                    raise ValidationError('Informe pelo menos 1 item da NF.')
                PagamentoNotaFiscalItem.objects.bulk_create(itens_objs)

                total_itens = nf.total_itens()
                pg = pagamento_form.save(commit=False)
                if pagamento_form.cleaned_data.get('tipo'):
                    pg.pagamento_nf = nf
                    # Defaults desejados
                    if not pg.data:
                        pg.data = nf.data_emissao
                    if not pg.valor or pg.valor == 0:
                        pg.valor = total_itens
                    pg.full_clean()
                    pg.save()

                    # Boletos só se tipo == boletos
                    if pg.tipo == PagamentoNotaFiscalPagamento.TipoPagamento.BOLETOS:
                        boletos = []
                        for bf in boletos_fs:
                            if not getattr(bf, 'cleaned_data', None):
                                continue
                            if bf.cleaned_data.get('DELETE'):
                                continue
                            boletos.append(
                                BoletoPagamento(
                                    pagamento_nf=nf,
                                    numero_doc=bf.cleaned_data['numero_doc'],
                                    parcela=bf.cleaned_data['parcela'],
                                    vencimento=bf.cleaned_data['vencimento'],
                                    valor=bf.cleaned_data['valor'],
                                    status=BoletoPagamento.Status.RASCUNHO,
                                )
                            )
                        if not boletos:
                            raise ValidationError(
                                'Pagamento por boletos exige gerar e salvar ao menos 1 boleto.'
                            )
                        for b in boletos:
                            b.full_clean()
                        BoletoPagamento.objects.bulk_create(boletos)

            messages.success(request, 'Pagamento por NF registrado.')
            return redirect_empresa(request, 'financeiro:dashboard')

    return render(
        request,
        'financeiro/pagamento_nf_form.html',
        {
            'page_title': 'Nota Fiscal',
            'form': form,
            'itens_fs': itens_fs,
            'pagamento_form': pagamento_form,
            'boletos_fs': boletos_fs,
            'modo': 'novo',
            'dup_nf': dup_nf,
            'show_dup_modal': bool(dup_nf) and request.method == 'POST' and not force_save,
            'active_tab': (request.GET.get('tab') or 'descricao').strip().lower(),
            'pagamento_tipo_boletos': PagamentoNotaFiscalPagamento.TipoPagamento.BOLETOS,
        },
    )


@login_required
def pagamento_nf_editar(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')

    nf = get_object_or_404(PagamentoNotaFiscal.objects.filter(empresa=empresa), pk=pk)
    form = PagamentoNotaFiscalForm(request.POST or None, instance=nf, empresa=empresa)
    # Para edição: por ora, regrava itens apagando e recriando (MVP).
    itens_fs = PagamentoNotaFiscalItemEditFormSet(
        request.POST or None,
        prefix='itens',
        form_kwargs={
            'empresa': empresa,
            'default_caixa_id': nf.caixa_id,
        },
        initial=[
            {
                'tipo': i.tipo,
                'descricao': i.descricao,
                'categoria': i.categoria_id,
                'quantidade': i.quantidade,
                'unidade': i.unidade,
                'valor_unitario': format_decimal_br_moeda(i.valor_unitario),
                'valor_total': format_decimal_br_moeda(i.valor_total),
                'caixa': i.caixa_id,
            }
            for i in nf.itens.all().order_by('pk')
        ],
    )
    pg_inst = getattr(nf, 'pagamento', None)
    pagamento_form = PagamentoNotaFiscalPagamentoForm(
        request.POST or None, instance=pg_inst, prefix='pg'
    )
    boletos_fs = BoletoRascunhoFormSet(
        request.POST or None,
        prefix='boletos',
        initial=[
            {
                'numero_doc': b.numero_doc,
                'parcela': b.parcela,
                'vencimento': b.vencimento.isoformat() if b.vencimento else '',
                'valor': format_decimal_br_moeda(b.valor),
            }
            for b in nf.boletos.all().order_by('vencimento', 'parcela', 'pk')
        ],
    )
    dup_nf = None
    force_save = str(request.POST.get('force_save', '')).strip() == '1'
    pagamento_tipo_anterior = pg_inst.tipo if pg_inst else ''

    if request.method == 'POST':
        ok = (
            form.is_valid()
            and itens_fs.is_valid()
            and pagamento_form.is_valid()
            and boletos_fs.is_valid()
        )
        if ok:
            cd = form.cleaned_data
            dup_nf = (
                PagamentoNotaFiscal.objects.filter(
                    empresa=empresa,
                    fornecedor=cd['fornecedor'],
                    numero_nf=cd['numero_nf'],
                )
                .exclude(pk=nf.pk)
                .order_by('-pk')
                .first()
            )
            if dup_nf and not force_save:
                ok = False

        if ok:
            with transaction.atomic():
                nf = form.save()

                nf.itens.all().delete()
                itens_objs = []
                for f in itens_fs:
                    if not getattr(f, 'cleaned_data', None):
                        continue
                    if f.cleaned_data.get('DELETE'):
                        continue
                    if f.cleaned_data.get('_skip_form'):
                        continue
                    item = f.save(commit=False)
                    item.pagamento_nf = nf
                    if not item.caixa_id:
                        item.caixa = nf.caixa
                    item.full_clean()
                    itens_objs.append(item)
                if not itens_objs:
                    raise ValidationError('Informe pelo menos 1 item da NF.')
                PagamentoNotaFiscalItem.objects.bulk_create(itens_objs)

                total_itens = nf.total_itens()
                pg = pagamento_form.save(commit=False)
                novo_tipo_pagamento = pagamento_form.cleaned_data.get('tipo')
                # Pagamento opcional: se tipo vazio, remove pagamento/boletos (rascunho) e mantém NF.
                if not novo_tipo_pagamento:
                    nf.boletos.all().delete()
                    PagamentoNotaFiscalPagamento.objects.filter(pagamento_nf=nf).delete()
                else:
                    if pagamento_tipo_anterior and pagamento_tipo_anterior != novo_tipo_pagamento:
                        nf.boletos.all().delete()
                        PagamentoNotaFiscalPagamento.objects.filter(pagamento_nf=nf).delete()
                        pg.pk = None
                    pg.pagamento_nf = nf
                    if not pg.data:
                        pg.data = nf.data_emissao
                    if not pg.valor or pg.valor == 0:
                        pg.valor = total_itens
                    pg.full_clean()
                    pg.save()

                    nf.boletos.all().delete()
                    if pg.tipo == PagamentoNotaFiscalPagamento.TipoPagamento.BOLETOS:
                        boletos = []
                        for bf in boletos_fs:
                            if not getattr(bf, 'cleaned_data', None):
                                continue
                            if bf.cleaned_data.get('DELETE'):
                                continue
                            boletos.append(
                                BoletoPagamento(
                                    pagamento_nf=nf,
                                    numero_doc=bf.cleaned_data['numero_doc'],
                                    parcela=bf.cleaned_data['parcela'],
                                    vencimento=bf.cleaned_data['vencimento'],
                                    valor=bf.cleaned_data['valor'],
                                    status=BoletoPagamento.Status.RASCUNHO,
                                )
                            )
                        if not boletos:
                            raise ValidationError(
                                'Pagamento por boletos exige gerar e salvar ao menos 1 boleto.'
                            )
                        for b in boletos:
                            b.full_clean()
                        BoletoPagamento.objects.bulk_create(boletos)

            messages.success(request, 'Pagamento por NF atualizado.')
            return redirect_empresa(request, 'financeiro:dashboard')

    return render(
        request,
        'financeiro/pagamento_nf_form.html',
        {
            'page_title': 'Nota Fiscal',
            'form': form,
            'itens_fs': itens_fs,
            'pagamento_form': pagamento_form,
            'boletos_fs': boletos_fs,
            'modo': 'editar',
            'nf': nf,
            'dup_nf': dup_nf,
            'show_dup_modal': bool(dup_nf) and request.method == 'POST' and not force_save,
            'active_tab': (request.GET.get('tab') or 'descricao').strip().lower(),
            'pagamento_tipo_boletos': PagamentoNotaFiscalPagamento.TipoPagamento.BOLETOS,
        },
    )


@login_required
def pagamento_nf_detalhe(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')

    nf = get_object_or_404(
        PagamentoNotaFiscal.objects.filter(empresa=empresa).select_related(
            'fornecedor',
            'caixa',
        ),
        pk=pk,
    )
    itens = list(
        nf.itens.select_related('categoria', 'caixa').order_by('pk')
    )
    pagamento = getattr(nf, 'pagamento', None)
    hoje = timezone.localdate()
    boletos = [
        _aplicar_situacao_boleto(boleto, hoje)
        for boleto in nf.boletos.order_by('vencimento', 'parcela', 'pk')
    ]
    pode_pagar_boletos = any(
        boleto.status not in (
            BoletoPagamento.Status.PAGO,
            BoletoPagamento.Status.CANCELADO,
        )
        for boleto in boletos
    )

    total_itens = nf.total_itens()
    total_boletos = sum((b.valor for b in boletos), Decimal('0'))
    resumo_pagamento = _resumo_pagamento_nf(pagamento, boletos, total_itens, hoje)

    return render(
        request,
        'financeiro/pagamento_nf_detalhe.html',
        {
            'page_title': f'Nota Fiscal nº {nf.numero_nf}',
            'nf': nf,
            'itens': itens,
            'pagamento': pagamento,
            'boletos': boletos,
            'pode_pagar_boletos': pode_pagar_boletos,
            'total_itens': total_itens,
            'total_boletos': total_boletos,
            'resumo_pagamento': resumo_pagamento,
        },
    )


@login_required
def pagamento_nf_pagar_boleto(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')

    nf = get_object_or_404(
        PagamentoNotaFiscal.objects.filter(empresa=empresa).select_related('fornecedor'),
        pk=pk,
    )
    detalhe_url = reverse_empresa(
        request,
        'financeiro:pagamento_nf_detalhe',
        kwargs={'pk': nf.pk},
    )
    boletos_qs = nf.boletos.exclude(status=BoletoPagamento.Status.CANCELADO).order_by(
        'vencimento', 'parcela', 'pk'
    )
    selected_boleto = None
    selected_boleto_id = (
        request.POST.get('boleto')
        or request.GET.get('boleto')
    )
    if selected_boleto_id:
        selected_boleto = boletos_qs.filter(pk=selected_boleto_id).first()
    if not selected_boleto:
        selected_boleto = (
            boletos_qs.exclude(status=BoletoPagamento.Status.PAGO).first()
            or boletos_qs.first()
        )
        if selected_boleto:
            selected_boleto_id = str(selected_boleto.pk)
    modo = 'editar' if selected_boleto and selected_boleto.status == BoletoPagamento.Status.PAGO else 'pagar'

    if request.method == 'POST':
        action = request.POST.get('action') or 'salvar'
        form = BoletoPagamentoForm(request.POST, boletos=boletos_qs, selected_boleto=selected_boleto)
        if action == 'excluir_pagamento':
            boleto = get_object_or_404(boletos_qs, pk=request.POST.get('boleto'))
            with transaction.atomic():
                boleto.status = BoletoPagamento.Status.RASCUNHO
                boleto.data_pagamento = None
                boleto.acrescimos = Decimal('0')
                boleto.descontos = Decimal('0')
                boleto.valor_pago = None
                boleto.observacao = ''
                boleto.full_clean()
                boleto.save(
                    update_fields=[
                        'status',
                        'data_pagamento',
                        'acrescimos',
                        'descontos',
                        'valor_pago',
                        'observacao',
                        'atualizado_em',
                    ]
                )
            messages.success(request, f'Pagamento do boleto {boleto.numero_doc} excluído.')
            if _is_htmx(request):
                response = HttpResponse(status=200)
                response['HX-Redirect'] = detalhe_url
                return response
            return redirect(detalhe_url)
        if form.is_valid():
            boleto = form.cleaned_data['boleto']
            with transaction.atomic():
                boleto.data_pagamento = form.cleaned_data['data_pagamento']
                boleto.acrescimos = form.cleaned_data['acrescimos']
                boleto.descontos = form.cleaned_data['descontos']
                boleto.valor_pago = form.cleaned_data['valor_pago']
                boleto.observacao = form.cleaned_data['observacao']
                boleto.status = BoletoPagamento.Status.PAGO
                boleto.full_clean()
                boleto.save(
                    update_fields=[
                        'data_pagamento',
                        'acrescimos',
                        'descontos',
                        'valor_pago',
                        'observacao',
                        'status',
                        'atualizado_em',
                    ]
                )
            messages.success(request, f'Boleto {boleto.numero_doc} pago com sucesso.')
            if _is_htmx(request):
                response = HttpResponse(status=200)
                response['HX-Redirect'] = detalhe_url
                return response
            return redirect(detalhe_url)
    else:
        form = BoletoPagamentoForm(boletos=boletos_qs, selected_boleto=selected_boleto)
        if not _is_htmx(request):
            return redirect(detalhe_url)

    boletos_abertos = [
        _aplicar_situacao_boleto(boleto)
        for boleto in boletos_qs
    ]
    if not boletos_abertos:
        messages.info(request, 'Não há boletos disponíveis para pagamento.')
        if _is_htmx(request):
            response = HttpResponse(status=200)
            response['HX-Redirect'] = detalhe_url
            return response
        return redirect(detalhe_url)

    if not selected_boleto_id and boletos_abertos:
        selected_boleto_id = str(boletos_abertos[0].pk)
    for boleto in boletos_abertos:
        boleto.is_selected = str(boleto.pk) == str(selected_boleto_id)

    return render(
        request,
        'financeiro/partials/pagamento_nf_pagar_boleto_modal.html',
        {
            'nf': nf,
            'form': form,
            'boletos': boletos_abertos,
            'selected_boleto_id': selected_boleto_id,
            'selected_boleto': selected_boleto,
            'modo': modo,
        },
    )


@login_required
def pagamento_nf_excluir(request, pk: int):
    empresa = _empresa(request)
    if not empresa:
        return redirect('selecionar_empresa')

    nf = get_object_or_404(
        PagamentoNotaFiscal.objects.filter(empresa=empresa).select_related(
            'fornecedor',
            'pagamento',
        ),
        pk=pk,
    )
    numero_nf = nf.numero_nf

    if request.method != 'POST':
        if not _is_htmx(request):
            return redirect_empresa(
                request,
                'financeiro:pagamento_nf_detalhe',
                kwargs={'pk': nf.pk},
            )
        boletos = list(nf.boletos.order_by('vencimento', 'parcela', 'pk'))
        pagamento = getattr(nf, 'pagamento', None)
        total_boletos = sum((boleto.valor for boleto in boletos), Decimal('0'))
        total_pago_boletos = sum(
            (boleto.valor_pago or Decimal('0') for boleto in boletos),
            Decimal('0'),
        )
        return render(
            request,
            'financeiro/partials/pagamento_nf_excluir_modal.html',
            {
                'nf': nf,
                'pagamento': pagamento,
                'boletos': boletos,
                'total_boletos': total_boletos,
                'total_pago_boletos': total_pago_boletos,
            },
        )

    with transaction.atomic():
        nf.boletos.all().delete()
        PagamentoNotaFiscalPagamento.objects.filter(pagamento_nf=nf).delete()
        nf.delete()

    messages.success(
        request,
        f'Nota Fiscal nº {numero_nf} excluída com pagamento e boletos vinculados.',
    )
    if _is_htmx(request):
        response = HttpResponse(status=200)
        response['HX-Redirect'] = reverse_empresa(request, 'financeiro:dashboard')
        return response
    return redirect_empresa(request, 'financeiro:dashboard')
