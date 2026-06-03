from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from clientes.models import Cliente
from empresas.models import Empresa
from usuarios.models import UsuarioEmpresa

from .models import Obra
from .scope import obras_queryset
from .views import modal_editar


class ObrasEmpresasAcessiveisTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(
            username='obras-user',
            password='senha-teste',
        )
        self.empresa_a = Empresa.objects.create(
            razao_social='Empresa A Ltda',
            nome_fantasia='Empresa A',
            cnpj='30.000.000/0001-00',
        )
        self.empresa_b = Empresa.objects.create(
            razao_social='Empresa B Ltda',
            nome_fantasia='Empresa B',
            cnpj='40.000.000/0001-00',
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
            nome='Obra A',
            contratante=self.cliente_a,
        )
        self.obra_b = Obra.objects.create(
            empresa=self.empresa_b,
            nome='Obra B',
            contratante=self.cliente_b,
        )
        UsuarioEmpresa.objects.create(
            usuario=self.user,
            empresa=self.empresa_b,
            ativo=True,
            obras=True,
        )

    def _request(self, permitir=False):
        vinculo = UsuarioEmpresa.objects.create(
            usuario=self.user,
            empresa=self.empresa_a,
            ativo=True,
            obras=True,
            obras_empresas_acessiveis=permitir,
        )
        request = self.factory.get('/', HTTP_HX_REQUEST='true')
        request.user = self.user
        request.empresa_ativa = self.empresa_a
        request.usuario_vinculo_empresa = vinculo
        request.usuario_obras_empresas_acessiveis = permitir
        request.usuario_admin_empresa = True
        return request

    def test_sem_permissao_lista_somente_obras_da_empresa_ativa(self):
        request = self._request(permitir=False)

        self.assertEqual(
            list(obras_queryset(request, self.empresa_a)),
            [self.obra_a],
        )

    def test_com_permissao_lista_obras_de_empresas_acessiveis(self):
        request = self._request(permitir=True)

        self.assertCountEqual(
            list(obras_queryset(request, self.empresa_a)),
            [self.obra_a, self.obra_b],
        )

    def test_modal_editar_obra_de_outra_empresa_usa_contratantes_da_obra(self):
        request = self._request(permitir=True)

        response = modal_editar(request, self.obra_b.pk)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Editar — Obra B · Empresa B', content)
        self.assertIn('Cliente B', content)
        self.assertNotIn('Cliente A', content)
