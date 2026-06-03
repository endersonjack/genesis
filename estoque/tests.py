from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from clientes.models import Cliente
from empresas.models import Empresa
from obras.models import Obra
from obras.scope import aplicar_obra_labels
from rh.models import Funcionario
from usuarios.models import UsuarioEmpresa

from .cautela_forms import CautelaForm
from .funcionarios_scope import aplicar_autocomplete_labels
from .requisicoes_forms import RequisicaoEstoqueForm


class EstoqueFuncionariosEmpresasAcessiveisTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(
            username='estoque-user',
            password='senha-teste',
        )
        self.empresa_a = Empresa.objects.create(
            razao_social='Empresa A Ltda',
            nome_fantasia='Empresa A',
            cnpj='10.000.000/0001-00',
        )
        self.empresa_b = Empresa.objects.create(
            razao_social='Empresa B Ltda',
            nome_fantasia='Empresa B',
            cnpj='20.000.000/0001-00',
        )
        self.func_a = Funcionario.objects.create(
            empresa=self.empresa_a,
            nome='João Silva',
            cpf='111.111.111-11',
        )
        self.func_b = Funcionario.objects.create(
            empresa=self.empresa_b,
            nome='João Silva',
            cpf='222.222.222-22',
        )
        self.cliente_a = Cliente.objects.create(
            empresa=self.empresa_a,
            nome='Cliente A',
        )
        self.cliente_b = Cliente.objects.create(
            empresa=self.empresa_b,
            nome='Cliente B',
        )
        self.obra_a = Obra.objects.create(
            empresa=self.empresa_a,
            nome='Obra Centro',
            contratante=self.cliente_a,
        )
        self.obra_b = Obra.objects.create(
            empresa=self.empresa_b,
            nome='Obra Centro',
            contratante=self.cliente_b,
        )
        UsuarioEmpresa.objects.create(
            usuario=self.user,
            empresa=self.empresa_b,
            ativo=True,
            obras=True,
        )

    def _request(self, permitir=False, permitir_obras=False):
        vinculo = UsuarioEmpresa.objects.create(
            usuario=self.user,
            empresa=self.empresa_a,
            ativo=True,
            estoque=True,
            estoque_funcionarios_empresas_acessiveis=permitir,
            obras=True,
            obras_empresas_acessiveis=permitir_obras,
        )
        request = self.factory.get('/')
        request.user = self.user
        request.empresa_ativa = self.empresa_a
        request.usuario_vinculo_empresa = vinculo
        request.usuario_estoque_funcionarios_empresas_acessiveis = permitir
        request.usuario_obras_empresas_acessiveis = permitir_obras
        return request

    def test_sem_permissao_estoque_lista_somente_funcionarios_da_empresa_ativa(self):
        form = RequisicaoEstoqueForm(
            empresa=self.empresa_a,
            request=self._request(permitir=False),
        )

        self.assertEqual(
            list(form.fields['solicitante'].queryset),
            [self.func_a],
        )

    def test_com_permissao_estoque_lista_funcionarios_de_empresas_acessiveis(self):
        form = CautelaForm(
            empresa=self.empresa_a,
            request=self._request(permitir=True),
        )

        self.assertCountEqual(
            list(form.fields['funcionario'].queryset),
            [self.func_a, self.func_b],
        )
        self.assertEqual(
            form.fields['funcionario'].label_from_instance(self.func_b),
            'João Silva · Empresa B',
        )

    def test_autocomplete_label_mostra_empresa_apenas_quando_for_outra_empresa(self):
        items = aplicar_autocomplete_labels([self.func_a, self.func_b], self.empresa_a)

        self.assertEqual(items[0].autocomplete_label, 'João Silva')
        self.assertEqual(items[1].autocomplete_label, 'João Silva · Empresa B')

    def test_sem_permissao_obras_no_estoque_lista_somente_empresa_ativa(self):
        form = RequisicaoEstoqueForm(
            empresa=self.empresa_a,
            request=self._request(permitir_obras=False),
        )

        self.assertEqual(
            list(form.fields['obra'].queryset),
            [self.obra_a],
        )

    def test_com_permissao_obras_no_estoque_lista_empresas_acessiveis(self):
        form = CautelaForm(
            empresa=self.empresa_a,
            request=self._request(permitir_obras=True),
        )

        self.assertCountEqual(
            list(form.fields['obra'].queryset),
            [self.obra_a, self.obra_b],
        )
        self.assertEqual(
            form.fields['obra'].label_from_instance(self.obra_b),
            'Obra Centro · Empresa B',
        )

    def test_autocomplete_label_obra_mostra_empresa_apenas_quando_for_outra_empresa(self):
        items = aplicar_obra_labels([self.obra_a, self.obra_b], self.empresa_a)

        self.assertEqual(items[0].autocomplete_label, 'Obra Centro')
        self.assertEqual(items[1].autocomplete_label, 'Obra Centro · Empresa B')
