from datetime import date
from unittest.mock import patch
from django.test import SimpleTestCase, RequestFactory
from django.core.exceptions import ValidationError
from .views import _periodo_caixa_unificado_params, _filtrar_linhas_periodo

class PeriodoCaixaTests(SimpleTestCase):
    def periodo(self, **params):
        return _periodo_caixa_unificado_params(RequestFactory().get("/", params))

    @patch("financeiro.views.timezone.localdate", return_value=date(2026, 10, 16))
    def test_padrao_mes_atual(self, mocked):
        p = self.periodo()
        self.assertEqual(p["data_inicio"], "2026-10-01")
        self.assertEqual(p["data_fim"], "2026-10-31")
        self.assertEqual(p["fim"], date(2026, 11, 1))

    def test_inclui_dia_final_e_cruza_ano(self):
        p = self.periodo(data_inicio="2025-12-31", data_fim="2026-01-02")
        rows = [{"data": date(2025, 12, 30)}, {"data": date(2025, 12, 31)},
                {"data": date(2026, 1, 2)}, {"data": date(2026, 1, 3)}]
        self.assertEqual(_filtrar_linhas_periodo(rows, p["inicio"], p["fim"]), rows[1:3])

    def test_mesmo_dia(self):
        p = self.periodo(data_inicio="2026-10-16", data_fim="2026-10-16")
        self.assertEqual(p["fim"], date(2026, 10, 17))

    @patch("financeiro.views.timezone.localdate", return_value=date(2024, 2, 10))
    def test_fevereiro_bissexto(self, mocked):
        self.assertEqual(self.periodo()["data_fim"], "2024-02-29")

    def test_rejeita_datas_invalidas_e_invertidas(self):
        for params in ({"data_inicio": "2026-02-30"}, {"data_fim": "abc"},
                       {"data_inicio": "2026-10-20", "data_fim": "2026-10-01"}):
            with self.subTest(params=params), self.assertRaises(ValidationError):
                self.periodo(**params)


class SelecaoCaixaTests(SimpleTestCase):
    def rows(self):
        from decimal import Decimal
        return [
            {"data": date(2026, 10, 1), "sort_key": (date(2026, 10, 1), pk, 50),
             "caixa_id": 1, "entrada": False, "valor": Decimal("100"),
             "natureza": "saida", "origem": "Boleto pago", "descricao": "Boleto"}
            for pk in (1, 2)
        ]

    def test_selecao_padrao_e_exclusao_por_id_estavel(self):
        from .views import _selecao_linhas_caixa
        rows = self.rows()
        self.assertEqual(len(_selecao_linhas_caixa(RequestFactory().get("/"), rows, "consolidado")), 2)
        request = RequestFactory().get("/", {"excluir": "consolidado:1:50:1"})
        selected = _selecao_linhas_caixa(request, list(reversed(rows)), "consolidado")
        self.assertEqual([r["selecao_id"] for r in selected], ["consolidado:1:50:2"])
        self.assertFalse(rows[0]["selecionada"])
        self.assertEqual(len(_selecao_linhas_caixa(request, rows, "detalhado")), 2)

    def test_tela_recalcula_totais_e_preserva_selecao_nos_links(self):
        from .views import caixa_unificado
        from empresas.models import Empresa
        from decimal import Decimal
        request = RequestFactory().get("/", {"modo": "consolidado",
            "data_inicio": "2026-10-01", "data_fim": "2026-10-31",
            "excluir": "consolidado:1:50:1"})
        empresa = Empresa(pk=1, razao_social="Teste")
        request.empresa_ativa = empresa
        with patch("financeiro.views._empresa", return_value=empresa), \
             patch("financeiro.views._caixas_com_saldo", return_value=[object()]), \
             patch("financeiro.views._extrato_caixa", side_effect=lambda *a, **k: self.rows()), \
             patch("financeiro.views._extrato_caixa_detalhado", return_value=[]), \
             patch("financeiro.views.render", side_effect=lambda req, tpl, ctx: ctx):
            context = caixa_unificado.__wrapped__(request)
            self.assertEqual(context["saidas_total"], Decimal("100"))
            self.assertEqual(context["total_selecionadas"], 1)
            self.assertEqual(context["paginator"].count, 2)
            self.assertIn("excluir=", context["pdf_url"])
            self.assertIn("excluir=", context["page_query"])
            request.GET = request.GET.copy()
            request.GET["somente_selecionados"] = "1"
            context = caixa_unificado.__wrapped__(request)
            self.assertEqual(context["paginator"].count, 1)
            from .views import caixa_unificado_pdf, _pdf_totais_table
            with patch("financeiro.views._flowables_header_compact", return_value=[]), \
                 patch("financeiro.views._flowables_rodape_impressao", return_value=[]), \
                 patch("financeiro.views._pdf_totais_table", wraps=_pdf_totais_table) as totals:
                response = caixa_unificado_pdf.__wrapped__(request)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.content.startswith(b"%PDF"))
                self.assertEqual(totals.call_args.args, (Decimal("0"), Decimal("100"), Decimal("-100"), 1))
