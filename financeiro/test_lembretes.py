from datetime import date
from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.http import Http404
from django.template.loader import render_to_string
from empresas.models import Empresa
from fornecedores.models import Fornecedor
from .models import LembretePagamento, MovimentoCaixa
from .lembretes import LembretePagamentoForm, contexto_lembretes
from .views import dashboard, lembrete_acao

class LembretesTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(razao_social="Empresa lembrete", cnpj="11111111000111")
        self.fornecedor = Fornecedor.objects.create(empresa=self.empresa, nome="Locador", tipo="PJ", cpf_cnpj="22222222000122")
        self.user = get_user_model().objects.create_user(username="agenda")
        self.factory = RequestFactory()

    def criar(self, **kwargs):
        data = dict(empresa=self.empresa, fornecedor=self.fornecedor, descricao="Aluguel",
                    data_pagamento=date(2026, 1, 31), valor=Decimal("1000"), dia_recorrencia=31)
        data.update(kwargs)
        return LembretePagamento.objects.create(**data)

    def request(self, method="get", data=None):
        request = getattr(self.factory, method)("/", data or {})
        request.empresa_ativa = self.empresa
        request.user = self.user
        return request

    def test_recorrencia_preserva_dia_31(self):
        item = self.criar(tipo="recorrente")
        item.concluir()
        self.assertEqual(item.data_pagamento, date(2026, 2, 28))
        item.concluir()
        self.assertEqual(item.data_pagamento, date(2026, 3, 31))
        self.assertTrue(item.ativo)
        self.assertEqual(MovimentoCaixa.objects.count(), 0)

    def test_unico_conclui_sem_lancamento(self):
        item = self.criar()
        item.concluir()
        self.assertFalse(item.ativo)
        self.assertEqual(MovimentoCaixa.objects.count(), 0)

    @patch("financeiro.lembretes.timezone.localdate", return_value=date(2026, 10, 26))
    def test_antecedencia(self, mocked):
        self.criar(data_pagamento=date(2026, 10, 31), avisar=5)
        self.criar(data_pagamento=date(2026, 11, 2), avisar=1)
        context = contexto_lembretes(self.empresa)
        self.assertEqual(context["lembretes_avisos"], 1)
        self.assertEqual([x.status_texto for x in context["lembretes"]], ["Programado"])

    def test_fornecedor_de_outra_empresa_rejeitado(self):
        outra = Empresa.objects.create(razao_social="Outra", cnpj="33333333000133")
        form = LembretePagamentoForm({"descricao": "Teste", "fornecedor": self.fornecedor.pk,
            "data_pagamento": "2026-10-31", "valor": "100,00", "tipo": "unico", "avisar": "0"},
            empresa=outra)
        self.assertFalse(form.is_valid())
        self.assertIn("fornecedor", form.errors)

    def test_salvar_modal_valida_valor_e_dia_base(self):
        form = LembretePagamentoForm({"descricao": "Aluguel", "fornecedor": self.fornecedor.pk,
            "data_pagamento": "2026-10-31", "valor": "1.250,00", "tipo": "recorrente", "avisar": "7"},
            empresa=self.empresa)
        self.assertTrue(form.is_valid(), form.errors)
        item = form.save()
        self.assertEqual(item.dia_recorrencia, 31)
        self.assertEqual(item.valor, Decimal("1250"))

    def test_duplo_envio_nao_avanca_duas_ocorrencias(self):
        item = self.criar(tipo="recorrente")
        request = self.request("post", {"acao": "concluir", "ocorrencia": "2026-01-31"})
        self.assertEqual(lembrete_acao(request, item.pk).status_code, 302)
        self.assertEqual(lembrete_acao(request, item.pk).status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.data_pagamento, date(2026, 2, 28))

    def test_acao_de_outra_empresa_bloqueada(self):
        item = self.criar()
        request = self.request("post", {"acao": "desativar"})
        request.empresa_ativa = Empresa.objects.create(razao_social="Outra", cnpj="44444444000144")
        with self.assertRaises(Http404):
            lembrete_acao(request, item.pk)

    def test_dashboard_e_formulario_invalido_renderizam(self):
        self.criar()
        response = dashboard(self.request())
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("Lembretes de pagamentos", html)
        self.assertIn('name="busca"', html)
        self.assertIn("novoLembreteModal", html)
        response = dashboard(self.request("post", {"descricao": "Incompleto"}))
        self.assertEqual(response.status_code, 400)
        self.assertIn('getOrCreateInstance(modal).show()', response.content.decode())


    def test_concluido_permanece_visivel_verde(self):
        item = self.criar()
        item.concluir()
        ctx = contexto_lembretes(self.empresa)
        self.assertEqual(len(ctx["lembretes"]), 1)
        self.assertTrue(ctx["lembretes"][0].concluido)
        self.assertEqual(ctx["lembretes_avisos"], 0)
        html = dashboard(self.request()).content.decode()
        self.assertIn('btn btn-success lembrete-acao-redonda', html)

    def test_recorrente_unico_reabre_apenas_na_data_do_aviso(self):
        item = self.criar(tipo="recorrente", avisar=7)
        item.concluir()
        with patch("financeiro.lembretes.timezone.localdate", return_value=date(2026, 2, 20)):
            rows = contexto_lembretes(self.empresa)["lembretes"]
            self.assertEqual(len(rows), 1)
            self.assertTrue(rows[0].concluido)
            self.assertEqual(rows[0].data_exibicao, date(2026, 1, 31))
        with patch("financeiro.lembretes.timezone.localdate", return_value=date(2026, 2, 21)):
            ctx = contexto_lembretes(self.empresa)
            rows = ctx["lembretes"]
            self.assertEqual(len(rows), 1)
            self.assertFalse(rows[0].concluido)
            self.assertEqual(rows[0].status_texto, "Programado")
            self.assertEqual(rows[0].data_exibicao, date(2026, 2, 28))
            self.assertEqual(ctx["lembretes_avisos"], 1)
        self.assertEqual(LembretePagamento.objects.count(), 1)
        request = self.request("post", {"acao": "desativar"})
        lembrete_acao(request, item.pk)
        self.assertEqual(contexto_lembretes(self.empresa)["lembretes"], [])

    def test_desativar_somente_no_modal(self):
        item = self.criar()
        html = dashboard(self.request()).content.decode()
        self.assertNotIn('form="desativarLembreteForm"', html)
        html = dashboard(self.request(data={"editar_lembrete": item.pk})).content.decode()
        self.assertIn('form="desativarLembreteForm"', html)
        self.assertIn('id="desativarLembreteForm"', html)
