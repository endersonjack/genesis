from decimal import Decimal
from types import SimpleNamespace

from django.test import RequestFactory, SimpleTestCase, TestCase

from empresas.models import Empresa
from financeiro.models import ContaBancaria
from controles_rh.forms import (
    AlteracaoFolhaLinhaForm,
    PagamentoSalarioControleForm,
    PagamentoSalarioLinhaForm,
    PremiacaoFuncionarioForm,
)
from controles_rh.models import (
    AlteracaoFolhaLinha,
    Competencia,
    PagamentoSalarioControle,
    PagamentoSalarioLinha,
    PremiacaoFuncionario,
)
from controles_rh.views.alteracao_folha import _fmt_af_horas, _fmt_celula_faltas
from controles_rh.views.pagamento_salario import (
    garantir_linhas_pagamento_salario,
    limpar_dados_pagamento_salario,
    _queryset_linhas,
)
from controles_rh.views.ps_export import (
    exportar_pagamento_salario_pdf,
    exportar_pagamento_salario_por_banco_pdf,
)
from rh.models import Funcionario


class AlteracaoFolhaFaltasTextoTests(SimpleTestCase):
    def test_falta_parcial_preserva_descricao_completa(self):
        texto = _fmt_celula_faltas({
            'dias': set(),
            'parciais': [{'dia': 26, 'descricao': '10h30m'}],
        })

        self.assertEqual(texto, '10h30m parcial (26)')

    def test_falta_parcial_agrupa_mesma_descricao_por_dia(self):
        texto = _fmt_celula_faltas({
            'dias': set(),
            'parciais': [
                {'dia': 27, 'descricao': '5h30m'},
                {'dia': 26, 'descricao': '5h30m'},
            ],
        })

        self.assertEqual(texto, '5h30m parcial (26,27)')

    def test_faltas_inteiras_e_parciais_compartilham_celula(self):
        texto = _fmt_celula_faltas({
            'dias': {18, 25},
            'parciais': [{'dia': 26, 'descricao': '5h30m'}],
        })

        self.assertEqual(texto, '2 (18,25) + 5h30m parcial (26)')


class AlteracaoFolhaHorasTests(TestCase):
    def test_form_aceita_horas_e_minutos(self):
        empresa = Empresa.objects.create(razao_social='Empresa Horas', cnpj='00.000.000/0002-00')
        competencia = Competencia.objects.create(empresa=empresa, mes=6, ano=2026)
        funcionario = Funcionario.objects.create(empresa=empresa, nome='Funcionário Horas', cpf='000.000.000-02')
        instance = AlteracaoFolhaLinha(competencia=competencia, funcionario=funcionario)
        form = AlteracaoFolhaLinhaForm(data={
            'hora_extra_horas': '1',
            'hora_extra_minutos': '30',
            'horas_feriado_horas': '0',
            'horas_feriado_minutos': '45',
            'adicional': '0.00',
            'outro_adicional': '0.00',
            'descontos': '0.00',
            'outro_desconto': '0.00',
        }, instance=instance)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['hora_extra'], Decimal('1.50'))
        self.assertEqual(form.cleaned_data['horas_feriado'], Decimal('0.75'))

    def test_form_initial_mostra_horas_e_minutos(self):
        form = AlteracaoFolhaLinhaForm(instance=AlteracaoFolhaLinha(
            hora_extra=Decimal('1.50'),
            horas_feriado=Decimal('0.75'),
        ))

        self.assertEqual(form.initial['hora_extra_horas'], 1)
        self.assertEqual(form.initial['hora_extra_minutos'], 30)
        self.assertEqual(form.initial['horas_feriado_horas'], 0)
        self.assertEqual(form.initial['horas_feriado_minutos'], 45)

    def test_formatador_de_horas_mostra_horas_e_minutos(self):
        self.assertEqual(_fmt_af_horas(Decimal('1.50')), '1h30m')
        self.assertEqual(_fmt_af_horas(Decimal('2.25')), '2h15m')


class PremiacaoFuncionarioFormTests(TestCase):
    def test_premio_anterior_e_media_sao_bloqueados(self):
        form = PremiacaoFuncionarioForm()

        self.assertTrue(form.fields['premio_anterior'].disabled)
        self.assertTrue(form.fields['media_premiacao'].disabled)

    def test_post_nao_altera_premio_anterior_e_media(self):
        empresa = Empresa.objects.create(razao_social='Empresa Teste', cnpj='00.000.000/0001-00')
        competencia = Competencia.objects.create(empresa=empresa, mes=6, ano=2026)
        funcionario = Funcionario.objects.create(empresa=empresa, nome='Funcionário Teste', cpf='000.000.000-00')
        instance = PremiacaoFuncionario.objects.create(
            competencia=competencia,
            funcionario=funcionario,
            premio_atual=Decimal('100.00'),
            premio_anterior=Decimal('250.00'),
            media_premiacao=Decimal('300.00'),
        )
        form = PremiacaoFuncionarioForm(
            data={
                'premio_atual': '150.00',
                'premio_anterior': '999,00',
                'media_premiacao': '888,00',
            },
            instance=instance,
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['premio_atual'], Decimal('150.00'))
        self.assertEqual(form.cleaned_data['premio_anterior'], Decimal('250.00'))
        self.assertEqual(form.cleaned_data['media_premiacao'], Decimal('300.00'))


class PagamentoSalarioTests(TestCase):
    def test_nome_exibicao_padrao(self):
        empresa = Empresa.objects.create(razao_social='Empresa Nome', cnpj='00.000.000/0007-00')
        competencia = Competencia.objects.create(empresa=empresa, mes=7, ano=2026)
        controle = PagamentoSalarioControle.objects.create(competencia=competencia)

        self.assertEqual(controle.nome_exibicao, 'Pagamento de salário')

    def test_form_dados_planilha_edita_nome(self):
        form = PagamentoSalarioControleForm(data={'nome': 'Salários Obra A'})

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['nome'], 'Salários Obra A')

    def test_permite_multiplas_planilhas_na_mesma_competencia(self):
        empresa = Empresa.objects.create(razao_social='Empresa Multi', cnpj='00.000.000/0010-00')
        competencia = Competencia.objects.create(empresa=empresa, mes=7, ano=2026)

        primeiro = PagamentoSalarioControle.objects.create(competencia=competencia)
        segundo = PagamentoSalarioControle.objects.create(
            competencia=competencia,
            nome='Pagamento complementar',
        )

        self.assertNotEqual(primeiro.pk, segundo.pk)
        self.assertEqual(
            PagamentoSalarioControle.objects.filter(competencia=competencia).count(),
            2,
        )

    def test_gera_linha_com_valor_zerado(self):
        empresa = Empresa.objects.create(razao_social='Empresa Pagamento', cnpj='00.000.000/0003-00')
        competencia = Competencia.objects.create(empresa=empresa, mes=7, ano=2026)
        funcionario = Funcionario.objects.create(
            empresa=empresa,
            nome='Funcionário Pagamento',
            cpf='000.000.000-03',
            salario=Decimal('2345.67'),
        )
        controle = PagamentoSalarioControle.objects.create(competencia=competencia)

        garantir_linhas_pagamento_salario(controle)

        linha = PagamentoSalarioLinha.objects.get(controle=controle, funcionario=funcionario)
        self.assertEqual(linha.valor, Decimal('0.00'))

    def test_form_initial_mostra_valor_em_pt_br(self):
        form = PagamentoSalarioLinhaForm(instance=PagamentoSalarioLinha(valor=Decimal('1234.50')))

        self.assertEqual(form.initial['valor'], '1234,50')

    def test_form_linha_lista_contas_ativas_da_empresa(self):
        empresa = Empresa.objects.create(razao_social='Empresa Banco', cnpj='00.000.000/0004-00')
        outra_empresa = Empresa.objects.create(razao_social='Outra Empresa Banco', cnpj='00.000.000/0005-00')
        conta_ativa = ContaBancaria.objects.create(
            empresa=empresa,
            nome='Conta Salário',
            banco='Santander',
            agencia='0001',
            conta='123',
        )
        conta_inativa = ContaBancaria.objects.create(
            empresa=empresa,
            nome='Conta Inativa',
            banco='Banco Inativo',
            agencia='0002',
            conta='456',
            ativo=False,
        )
        conta_outra_empresa = ContaBancaria.objects.create(
            empresa=outra_empresa,
            nome='Conta Outra',
            banco='Outro Banco',
            agencia='0003',
            conta='789',
        )

        form = PagamentoSalarioLinhaForm(empresa=empresa)

        queryset = form.fields['conta_bancaria_empresa'].queryset
        self.assertIn(conta_ativa, queryset)
        self.assertNotIn(conta_inativa, queryset)
        self.assertNotIn(conta_outra_empresa, queryset)

    def test_limpar_dados_zera_valor_e_remove_banco_empresa(self):
        empresa = Empresa.objects.create(razao_social='Empresa Limpar', cnpj='00.000.000/0006-00')
        competencia = Competencia.objects.create(empresa=empresa, mes=7, ano=2026)
        funcionario = Funcionario.objects.create(
            empresa=empresa,
            nome='Funcionário Limpar',
            cpf='000.000.000-06',
        )
        conta = ContaBancaria.objects.create(
            empresa=empresa,
            nome='Conta Limpar',
            banco='Santander',
            agencia='0001',
            conta='999',
        )
        controle = PagamentoSalarioControle.objects.create(competencia=competencia)
        linha = PagamentoSalarioLinha.objects.create(
            controle=controle,
            funcionario=funcionario,
            valor=Decimal('500.00'),
            conta_bancaria_empresa=conta,
        )

        total = limpar_dados_pagamento_salario(controle)

        linha.refresh_from_db()
        self.assertEqual(total, 1)
        self.assertEqual(linha.valor, Decimal('0.00'))
        self.assertIsNone(linha.conta_bancaria_empresa)

    def test_query_linhas_filtra_por_banco_empresa(self):
        empresa = Empresa.objects.create(razao_social='Empresa Filtro Banco', cnpj='00.000.000/0011-00')
        competencia = Competencia.objects.create(empresa=empresa, mes=7, ano=2026)
        banco_a = ContaBancaria.objects.create(
            empresa=empresa,
            nome='Conta A',
            banco='Banco A',
            agencia='0001',
            conta='111',
        )
        banco_b = ContaBancaria.objects.create(
            empresa=empresa,
            nome='Conta B',
            banco='Banco B',
            agencia='0002',
            conta='222',
        )
        func_a = Funcionario.objects.create(empresa=empresa, nome='Funcionário A', cpf='000.000.000-11')
        func_b = Funcionario.objects.create(empresa=empresa, nome='Funcionário B', cpf='000.000.000-12')
        controle = PagamentoSalarioControle.objects.create(competencia=competencia)
        PagamentoSalarioLinha.objects.create(
            controle=controle,
            funcionario=func_a,
            valor=Decimal('100.00'),
            conta_bancaria_empresa=banco_a,
        )
        PagamentoSalarioLinha.objects.create(
            controle=controle,
            funcionario=func_b,
            valor=Decimal('200.00'),
            conta_bancaria_empresa=banco_b,
        )

        qs = _queryset_linhas(controle, banco_empresa=str(banco_a.pk))

        self.assertEqual(list(qs.values_list('funcionario_id', flat=True)), [func_a.pk])

    def test_exportar_pdf_pagamento_salario(self):
        empresa = Empresa.objects.create(razao_social='Empresa PDF', cnpj='00.000.000/0008-00')
        competencia = Competencia.objects.create(empresa=empresa, mes=7, ano=2026)
        funcionario = Funcionario.objects.create(
            empresa=empresa,
            nome='Funcionário PDF',
            cpf='000.000.000-08',
        )
        controle = PagamentoSalarioControle.objects.create(
            competencia=competencia,
            nome='Salários PDF',
        )
        PagamentoSalarioLinha.objects.create(
            controle=controle,
            funcionario=funcionario,
            valor=Decimal('500.00'),
        )
        request = RequestFactory().get('/fake-url/')
        request.empresa_ativa = empresa
        request.user = SimpleNamespace(is_authenticated=False)

        response = exportar_pagamento_salario_pdf.__wrapped__(request, controle.pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_exportar_pdf_pagamento_salario_por_banco(self):
        empresa = Empresa.objects.create(razao_social='Empresa PDF Banco', cnpj='00.000.000/0012-00')
        competencia = Competencia.objects.create(empresa=empresa, mes=7, ano=2026)
        conta = ContaBancaria.objects.create(
            empresa=empresa,
            nome='Conta PDF',
            banco='Santander',
            agencia='0001',
            conta='999',
        )
        funcionario = Funcionario.objects.create(
            empresa=empresa,
            nome='Funcionário PDF Banco',
            cpf='000.000.000-13',
        )
        controle = PagamentoSalarioControle.objects.create(
            competencia=competencia,
            nome='Salários Banco PDF',
        )
        PagamentoSalarioLinha.objects.create(
            controle=controle,
            funcionario=funcionario,
            valor=Decimal('750.00'),
            conta_bancaria_empresa=conta,
        )
        request = RequestFactory().get('/fake-url/', {'banco_empresa': str(conta.pk)})
        request.empresa_ativa = empresa
        request.user = SimpleNamespace(is_authenticated=False)

        response = exportar_pagamento_salario_por_banco_pdf.__wrapped__(request, controle.pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
