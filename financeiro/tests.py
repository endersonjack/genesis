from django.test import TestCase
from django.test import RequestFactory

import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from empresas.models import Empresa
from fornecedores.models import Fornecedor
from usuarios.models import UsuarioEmpresa

from .models import (
    AutoridadeTributaria,
    BoletoPagamento,
    Caixa,
    CategoriaFinanceira,
    PagamentoImposto,
    PagamentoImpostoItem,
    PagamentoNotaFiscal,
    PagamentoNotaFiscalPagamento,
    PagamentoNotaFiscalItem,
)
from .views import (
    _busca_pagamentos_nf_corresponde_status,
    _dashboard_alertas_financeiro_data,
    relatorios,
    relatorio_fornecedor_pdf,
    _status_busca_pagamento_nf,
    pagamento_nf_detalhe,
    pagamento_nf_fornecedor_info,
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


class PagamentoNotaFiscalFornecedorInfoTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(
            username='financeiro',
            password='senha-teste',
        )
        self.empresa = Empresa.objects.create(
            razao_social='Empresa Teste',
            nome_fantasia='Empresa Teste',
            cnpj='11.111.111/0001-11',
        )
        self.caixa = Caixa.objects.get(
            empresa=self.empresa,
            tipo=Caixa.Tipo.GERAL,
        )
        self.fornecedor = Fornecedor.objects.create(
            empresa=self.empresa,
            tipo='PJ',
            cpf_cnpj='22222222000122',
            nome='Fornecedor Teste',
        )

    def _criar_nf(self, numero, data_emissao):
        return PagamentoNotaFiscal.objects.create(
            empresa=self.empresa,
            fornecedor=self.fornecedor,
            numero_nf=numero,
            data_emissao=data_emissao,
            caixa=self.caixa,
        )

    def test_fornecedor_info_ordena_ultimos_por_data_emissao_mais_recente(self):
        self._criar_nf('30', date(2026, 4, 30))
        self._criar_nf('10', date(2026, 4, 10))
        self._criar_nf('18', date(2026, 4, 18))
        self._criar_nf('29', date(2026, 4, 29))

        request = self.factory.get(
            '/pagamentos/nf/fornecedor-info/',
            {'fornecedor': self.fornecedor.pk},
        )
        request.user = self.user
        request.empresa_ativa = self.empresa

        response = pagamento_nf_fornecedor_info(request)
        data = json.loads(response.content)

        self.assertEqual(
            [linha['data'] for linha in data['ultimos']],
            ['30/04/2026', '29/04/2026', '18/04/2026', '10/04/2026'],
        )

    def test_relatorios_renderiza_card_fornecedor_com_itens_da_nf(self):
        categoria = CategoriaFinanceira.objects.create(
            empresa=self.empresa,
            tipo=CategoriaFinanceira.Tipo.SAIDA,
            movimentacao_tipo=CategoriaFinanceira.MovimentacaoTipo.PAGAMENTO_NOTA_FISCAL,
            nome='Material',
        )
        nf = self._criar_nf('77', date(2026, 4, 30))
        nf.descricao = 'Compra de insumos'
        nf.save(update_fields=['descricao'])
        PagamentoNotaFiscalItem.objects.create(
            pagamento_nf=nf,
            tipo=PagamentoNotaFiscalItem.TipoItem.PRODUTO,
            descricao='Cimento',
            categoria=categoria,
            quantidade=Decimal('2'),
            unidade='SC',
            valor_unitario=Decimal('50.00'),
            valor_total=Decimal('100.00'),
            caixa=self.caixa,
        )

        request = self.factory.get(
            '/relatorios/',
            {'rel_fornecedor': self.fornecedor.pk},
        )
        request.user = self.user
        request.empresa_ativa = self.empresa

        response = relatorios(request)
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn('Relatórios de Fornecedor', content)
        self.assertIn('Fornecedor Teste', content)
        self.assertIn('Cimento', content)
        self.assertIn('Compra de insumos', content)

    def test_relatorio_fornecedor_pdf_gera_pdf(self):
        nf = self._criar_nf('88', date(2026, 4, 30))
        PagamentoNotaFiscalItem.objects.create(
            pagamento_nf=nf,
            tipo=PagamentoNotaFiscalItem.TipoItem.PRODUTO,
            descricao='Areia',
            quantidade=Decimal('1'),
            unidade='M3',
            valor_unitario=Decimal('80.00'),
            valor_total=Decimal('80.00'),
            caixa=self.caixa,
        )

        request = self.factory.get(
            '/relatorios/fornecedor/pdf/',
            {'rel_fornecedor': self.fornecedor.pk},
        )
        request.user = self.user
        request.empresa_ativa = self.empresa

        response = relatorio_fornecedor_pdf(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))


class PagamentoNotaFiscalDetalheAcoesTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(
            username='financeiro-acoes',
            password='senha-teste',
        )
        self.empresa = Empresa.objects.create(
            razao_social='Empresa Ações',
            nome_fantasia='Empresa Ações',
            cnpj='33.333.333/0001-33',
        )
        self.caixa = Caixa.objects.get(
            empresa=self.empresa,
            tipo=Caixa.Tipo.GERAL,
        )
        self.fornecedor = Fornecedor.objects.create(
            empresa=self.empresa,
            tipo='PJ',
            cpf_cnpj='44444444000144',
            nome='Fornecedor Ações',
        )

    def _request(self):
        request = self.factory.get('/')
        request.user = self.user
        request.empresa_ativa = self.empresa
        return request

    def _criar_nf(self, numero='101'):
        nf = PagamentoNotaFiscal.objects.create(
            empresa=self.empresa,
            fornecedor=self.fornecedor,
            numero_nf=numero,
            data_emissao=date(2026, 6, 1),
            caixa=self.caixa,
        )
        PagamentoNotaFiscalItem.objects.create(
            pagamento_nf=nf,
            tipo=PagamentoNotaFiscalItem.TipoItem.PRODUTO,
            descricao='Material',
            quantidade=Decimal('1'),
            valor_unitario=Decimal('100.00'),
            valor_total=Decimal('100.00'),
            caixa=self.caixa,
        )
        return nf

    def test_nf_sem_boleto_mostra_pagar_para_aba_pagamento(self):
        nf = self._criar_nf()

        response = pagamento_nf_detalhe(self._request(), nf.pk)

        content = response.content.decode()
        self.assertIn('?tab=pagamento', content)
        self.assertNotIn('pagar-boleto', content)

    def test_nf_com_boleto_aberto_mostra_acoes_de_modal_para_boleto(self):
        nf = self._criar_nf()
        PagamentoNotaFiscalPagamento.objects.create(
            pagamento_nf=nf,
            tipo=PagamentoNotaFiscalPagamento.TipoPagamento.BOLETOS,
            data=date(2026, 6, 1),
            valor=Decimal('100.00'),
        )
        boleto = BoletoPagamento.objects.create(
            pagamento_nf=nf,
            numero_doc='BOL-101',
            parcela=1,
            vencimento=date(2026, 6, 10),
            valor=Decimal('100.00'),
            status=BoletoPagamento.Status.EMITIDO,
        )

        response = pagamento_nf_detalhe(self._request(), nf.pk)

        content = response.content.decode()
        self.assertIn('pagar-boleto/', content)
        self.assertIn(f'?boleto={boleto.pk}', content)
        self.assertIn('hx-target="#modal-content"', content)

    def test_pagamento_multiplo_de_boletos_salva_e_redireciona(self):
        UsuarioEmpresa.objects.create(
            usuario=self.user,
            empresa=self.empresa,
            ativo=True,
            financeiro=True,
        )
        self.client.force_login(self.user)
        nf = self._criar_nf()
        PagamentoNotaFiscalPagamento.objects.create(
            pagamento_nf=nf,
            tipo=PagamentoNotaFiscalPagamento.TipoPagamento.BOLETOS,
            data=date(2026, 6, 1),
            valor=Decimal('200.00'),
        )
        boleto_1 = BoletoPagamento.objects.create(
            pagamento_nf=nf,
            numero_doc='BOL-201',
            parcela=1,
            vencimento=date(2026, 6, 10),
            valor=Decimal('100.00'),
            status=BoletoPagamento.Status.EMITIDO,
        )
        boleto_2 = BoletoPagamento.objects.create(
            pagamento_nf=nf,
            numero_doc='BOL-202',
            parcela=2,
            vencimento=date(2026, 6, 20),
            valor=Decimal('100.00'),
            status=BoletoPagamento.Status.EMITIDO,
        )

        response = self.client.post(
            f'/empresa/{self.empresa.pk}/financeiro/pagamentos/nf/{nf.pk}/pagar-boleto/',
            {
                'action': 'salvar_multiplos',
                'boletos': [str(boleto_1.pk), str(boleto_2.pk)],
                f'data_pagamento_{boleto_1.pk}': '10/06/2026',
                f'data_pagamento_{boleto_2.pk}': '20/06/2026',
            },
            HTTP_HX_REQUEST='true',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['HX-Redirect'],
            f'/empresa/{self.empresa.pk}/financeiro/pagamentos/nf/{nf.pk}/',
        )
        boleto_1.refresh_from_db()
        boleto_2.refresh_from_db()
        self.assertEqual(boleto_1.status, BoletoPagamento.Status.PAGO)
        self.assertEqual(boleto_2.status, BoletoPagamento.Status.PAGO)
        self.assertEqual(boleto_1.valor_pago, Decimal('100.00'))
        self.assertEqual(boleto_2.valor_pago, Decimal('100.00'))
