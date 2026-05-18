from django.test import TestCase

from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from empresas.models import Empresa

from .models import (
    AutoridadeTributaria,
    BoletoPagamento,
    Caixa,
    CategoriaFinanceira,
    PagamentoImposto,
    PagamentoImpostoItem,
)
from .views import (
    _busca_pagamentos_nf_corresponde_status,
    _dashboard_alertas_financeiro_data,
    _status_busca_pagamento_nf,
)


class BuscarPagamentosStatusTests(TestCase):
    def test_status_pago_inclui_nf_com_pagamento_parcial(self):
        resumo = {
            'situacao_label': 'Pago Parcial',
            'valor_pago': Decimal('50.00'),
        }

        self.assertTrue(
            _busca_pagamentos_nf_corresponde_status(
                resumo,
                status_vencido=False,
                status_aberto=False,
                status_pago=True,
            )
        )

    def test_status_pago_inclui_nf_vencida_com_algum_pagamento(self):
        resumo = {
            'situacao_label': 'Vencido',
            'valor_pago': Decimal('50.00'),
        }

        self.assertTrue(
            _busca_pagamentos_nf_corresponde_status(
                resumo,
                status_vencido=False,
                status_aberto=False,
                status_pago=True,
            )
        )

    def test_status_pago_nao_inclui_nf_sem_pagamento(self):
        resumo = {
            'situacao_label': 'Não pago',
            'valor_pago': Decimal('0.00'),
        }

        self.assertFalse(
            _busca_pagamentos_nf_corresponde_status(
                resumo,
                status_vencido=False,
                status_aberto=False,
                status_pago=True,
            )
        )

    def test_status_coluna_marca_em_aberto_para_boleto_a_vencer_sem_pagamento(self):
        boleto = BoletoPagamento(
            vencimento=date(2026, 5, 7),
            status=BoletoPagamento.Status.EMITIDO,
            valor=Decimal('100.00'),
        )
        resumo = {
            'valor_pago': Decimal('0.00'),
        }

        self.assertEqual(
            _status_busca_pagamento_nf(
                resumo,
                [boleto],
                Decimal('100.00'),
                hoje=date(2026, 5, 6),
            ),
            'Em Aberto',
        )

    def test_status_coluna_marca_vence_hoje_para_boleto_com_vencimento_do_dia(self):
        boleto = BoletoPagamento(
            vencimento=date(2026, 5, 6),
            status=BoletoPagamento.Status.EMITIDO,
            valor=Decimal('100.00'),
        )
        resumo = {
            'valor_pago': Decimal('0.00'),
        }

        self.assertEqual(
            _status_busca_pagamento_nf(
                resumo,
                [boleto],
                Decimal('100.00'),
                hoje=date(2026, 5, 6),
            ),
            'Vence Hoje',
        )


class DashboardFinanceiroImpostosTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            razao_social='Empresa Teste',
            nome_fantasia='Empresa Teste',
            cnpj='00.000.000/0001-00',
        )
        self.caixa = Caixa.objects.get(
            empresa=self.empresa,
            tipo=Caixa.Tipo.GERAL,
        )
        self.autoridade = AutoridadeTributaria.objects.create(
            empresa=self.empresa,
            nome='Receita Federal',
            esfera=AutoridadeTributaria.Esfera.FEDERAL,
        )
        self.categoria = CategoriaFinanceira.objects.create(
            empresa=self.empresa,
            tipo=CategoriaFinanceira.Tipo.SAIDA,
            movimentacao_tipo=CategoriaFinanceira.MovimentacaoTipo.PAGAMENTO_IMPOSTOS,
            nome='Impostos',
        )

    def _criar_imposto(self, *, data_vencimento, valor, data_pagamento=None):
        imposto = PagamentoImposto.objects.create(
            empresa=self.empresa,
            autoridade=self.autoridade,
            data_emissao=timezone.localdate(),
            periodo_apuracao='05/2026',
            data_vencimento=data_vencimento,
            caixa=self.caixa,
            data_pagamento=data_pagamento,
        )
        PagamentoImpostoItem.objects.create(
            pagamento=imposto,
            descricao='COFINS/PIS',
            categoria=self.categoria,
            valor_total=valor,
        )
        return imposto

    def test_card_impostos_inclui_vencidos_e_em_aberto_sem_pagamento(self):
        hoje = timezone.localdate()
        imposto_vencido = self._criar_imposto(
            data_vencimento=hoje - timedelta(days=2),
            valor=Decimal('100.00'),
        )
        imposto_em_aberto = self._criar_imposto(
            data_vencimento=hoje + timedelta(days=10),
            valor=Decimal('200.00'),
        )
        imposto_pago = self._criar_imposto(
            data_vencimento=hoje - timedelta(days=1),
            valor=Decimal('300.00'),
            data_pagamento=hoje,
        )

        data = _dashboard_alertas_financeiro_data(self.empresa)

        linhas_por_pk = {
            linha['imposto_pk']: linha
            for linha in data['dashboard_impostos_vencidos_linhas']
        }
        self.assertIn(imposto_vencido.pk, linhas_por_pk)
        self.assertIn(imposto_em_aberto.pk, linhas_por_pk)
        self.assertNotIn(imposto_pago.pk, linhas_por_pk)
        self.assertEqual(linhas_por_pk[imposto_em_aberto.pk]['situacao'], 'Em Aberto')
        self.assertEqual(linhas_por_pk[imposto_em_aberto.pk]['dias_atrasados'], 0)
        self.assertEqual(data['total_impostos_vencidos'], Decimal('300.00'))
