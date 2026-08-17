from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from controles_rh.views.vt_export import (
    VT_PDF_TABLE_WIDTH_MM,
    _col_widths_vt_pdf_mm_for_items,
    _vt_pdf_pix_tipo_banco_html,
    _vt_pdf_valor_pago_html,
)


class _Pagamentos:
    def __init__(self, pagamentos):
        self._pagamentos = pagamentos

    def all(self):
        return self._pagamentos


def _item_vt(observacao=''):
    pagamentos = []
    valor_pago = Decimal('200.00')
    if observacao:
        pagamentos = [
            SimpleNamespace(
                valor=Decimal('100.00'),
                data_pagamento=date(2026, 7, 31),
                observacao=observacao,
            ),
            SimpleNamespace(
                valor=Decimal('100.00'),
                data_pagamento=date(2026, 8, 10),
                observacao='segunda parcela',
            ),
        ]
    return SimpleNamespace(
        nome_exibicao='Dióclecio Bento de Oliveira Junior',
        funcao='Motorista',
        funcionario_id=1,
        funcionario=SimpleNamespace(
            cpf='121.857.684-76',
            local_trabalho='Escritório - Brasil Construção',
        ),
        pagamentos=_Pagamentos(pagamentos),
        valor_pago=valor_pago,
        pix='09976142420',
        banco='Nubank',
        get_tipo_pix_display=lambda: 'CPF',
    )


class ValeTransportePdfLayoutTests(SimpleTestCase):
    def test_larguras_dinamicas_preservam_espaco_para_valor_pago(self):
        widths_short = _col_widths_vt_pdf_mm_for_items([_item_vt()])
        widths_long = _col_widths_vt_pdf_mm_for_items([
            _item_vt('passagens para seis dias (3 a 7, 10)')
        ])

        self.assertAlmostEqual(sum(widths_long), VT_PDF_TABLE_WIDTH_MM, places=6)
        self.assertLessEqual(widths_long[1], 105.0)
        self.assertGreaterEqual(widths_long[3], 42.0)
        self.assertGreater(widths_long[3], widths_short[3])

    def test_valor_pago_exibe_total_acima_dos_detalhes(self):
        html = _vt_pdf_valor_pago_html(
            _item_vt('passagens para seis dias (3 a 7, 10)')
        )

        self.assertTrue(html.startswith('<b>Total: R$ 200,00</b><br/>'))
        self.assertIn('R$ 100,00 - 31/07/2026 - passagens', html)
        self.assertIn('<br/>R$ 100,00 - 10/08/2026 - segunda parcela', html)

    def test_pix_e_tipo_ficam_acima_do_banco(self):
        html = _vt_pdf_pix_tipo_banco_html(_item_vt())

        self.assertEqual(html, '09976142420 - CPF<br/>NUBANK')

