from django.test import TestCase

from datetime import date
from decimal import Decimal

from .models import BoletoPagamento
from .views import _busca_pagamentos_nf_corresponde_status, _status_busca_pagamento_nf


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
