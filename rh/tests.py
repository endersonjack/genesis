from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from empresas.models import Empresa

from .forms import CurriculoForm
from .models import Cargo


class CurriculoFormTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            razao_social='Empresa Teste',
            nome_fantasia='Empresa Teste',
            cnpj='11.111.111/0001-11',
        )
        self.outra_empresa = Empresa.objects.create(
            razao_social='Outra Empresa',
            nome_fantasia='Outra Empresa',
            cnpj='22.222.222/0001-22',
        )
        self.cargo = Cargo.objects.create(empresa=self.empresa, nome='Pedreiro')
        self.cargo_outra_empresa = Cargo.objects.create(
            empresa=self.outra_empresa,
            nome='Armador',
        )

    def test_filtra_funcao_por_empresa_ativa(self):
        form = CurriculoForm(empresa_ativa=self.empresa)

        self.assertIn('data', form.fields)
        self.assertIn(self.cargo, form.fields['funcao'].queryset)
        self.assertNotIn(self.cargo_outra_empresa, form.fields['funcao'].queryset)

    def test_aceita_multiplos_anexos(self):
        form = CurriculoForm(
            data={
                'data': timezone.localdate().isoformat(),
                'nome': 'João Candidato',
                'funcao': self.cargo.pk,
                'telefone': '(11) 99999-9999',
                'email': 'joao@example.com',
                'endereco': 'Rua Teste',
                'indicacao': 'Maria',
                'status': 'novo',
                'observacoes': '',
            },
            files={
                'anexos': [
                    SimpleUploadedFile('curriculo.pdf', b'pdf', content_type='application/pdf'),
                    SimpleUploadedFile('certificado.pdf', b'pdf', content_type='application/pdf'),
                ],
            },
            empresa_ativa=self.empresa,
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.cleaned_data['anexos']), 2)
