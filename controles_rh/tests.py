from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from empresas.models import Empresa
from controles_rh.forms import AlteracaoFolhaLinhaForm, PremiacaoFuncionarioForm
from controles_rh.models import AlteracaoFolhaLinha, Competencia, PremiacaoFuncionario
from controles_rh.views.alteracao_folha import _fmt_af_horas, _fmt_celula_faltas
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
