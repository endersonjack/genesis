from datetime import date
from unittest.mock import patch
from django.test import TestCase, RequestFactory
from empresas.models import Empresa
from .models import Caixa, AutoridadeTributaria, CategoriaFinanceira, PagamentoImposto, PagamentoImpostoItem
from .views import pagamento_imposto_lista


class FiltroImpostosTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(razao_social='Filtros', cnpj='12345678000199')
        self.caixa = Caixa.objects.get(empresa=self.empresa, tipo=Caixa.Tipo.GERAL)
        self.autoridade = AutoridadeTributaria.objects.create(empresa=self.empresa, nome='Receita')
        self.categoria = CategoriaFinanceira.objects.create(
            empresa=self.empresa, nome='PIS', tipo='saida', movimentacao_tipo='pag_impostos')

    def criar(self, data):
        obj = PagamentoImposto.objects.create(empresa=self.empresa, caixa=self.caixa,
            autoridade=self.autoridade, data_pagamento=data)
        for valor in (10, 20):
            PagamentoImpostoItem.objects.create(pagamento=obj, categoria=self.categoria,
                descricao='Imposto', valor_total=valor)
        return obj

    def contexto(self, **params):
        request = RequestFactory().get('/', params)
        request.empresa_ativa = self.empresa
        with patch('financeiro.views.timezone.localdate', return_value=date(2026, 10, 27)), patch('financeiro.views.render') as render:
            pagamento_imposto_lista.__wrapped__(request)
        return render.call_args.args[2]

    def test_mes_atual_sem_limite_e_sem_abertos(self):
        for _ in range(21):
            self.criar(date(2026, 10, 1))
        self.criar(date(2026, 9, 30))
        self.criar(None)
        ctx = self.contexto()
        self.assertEqual(len(ctx['pagamentos_periodo']), 21)
        self.assertEqual(len(ctx['impostos_abertos']), 1)
        self.assertEqual(ctx['filtro_pagamentos']['data_inicio'].value(), '2026-10-01')
        self.assertEqual(ctx['filtro_pagamentos']['data_fim'].value(), '2026-10-31')

    def test_periodo_inclusivo_categoria_sem_duplicar_total(self):
        obj = self.criar(date(2026, 9, 30))
        self.criar(date(2026, 10, 1))
        ctx = self.contexto(data_inicio='2026-09-30', data_fim='2026-09-30', categoria=self.categoria.pk)
        self.assertEqual([p.pk for p in ctx['pagamentos_periodo']], [obj.pk])
        self.assertEqual(ctx['pagamentos_periodo'][0].total_itens_calc, 30)

    def test_filtros_invalidos_nao_retornam_pagamentos(self):
        self.criar(date(2026, 10, 1))
        for params in (
            {'data_inicio': 'invalida'},
            {'data_inicio': '2026-11-01', 'data_fim': '2026-10-01'},
            {'categoria': '999999'},
        ):
            ctx = self.contexto(**params)
            self.assertTrue(ctx['filtro_pagamentos'].errors)
            self.assertEqual(ctx['pagamentos_periodo'], [])

    def test_total_e_pdf_respeitam_periodo(self):
        self.criar(date(2026, 10, 1))
        self.criar(date(2026, 9, 30))
        ctx = self.contexto()
        self.assertEqual(ctx['total_pagamentos'], 30)
        self.assertIn('export=pdf', ctx['url_pdf'])
        request = RequestFactory().get('/', {'export': 'pdf'})
        request.empresa_ativa = self.empresa
        with patch('financeiro.views.timezone.localdate', return_value=date(2026, 10, 27)):
            response = pagamento_imposto_lista.__wrapped__(request)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
        self.assertIn('attachment', response['Content-Disposition'])

    def test_pdf_rejeita_periodo_invalido(self):
        request = RequestFactory().get('/', {'export': 'pdf', 'data_inicio': 'invalida'})
        request.empresa_ativa = self.empresa
        self.assertEqual(pagamento_imposto_lista.__wrapped__(request).status_code, 400)
