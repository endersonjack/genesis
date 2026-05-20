from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from empresas.models import Empresa

from .forms import CurriculoForm
from .models import Cargo, Curriculo


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
        self.assertIn('foto', form.fields)
        self.assertIn('cat_cnh', form.fields)
        self.assertIn('funcoes', form.fields)
        self.assertIn(self.cargo, form.fields['funcoes'].queryset)
        self.assertNotIn(self.cargo_outra_empresa, form.fields['funcoes'].queryset)

    def test_aceita_multiplos_anexos(self):
        form = CurriculoForm(
            data={
                'data': timezone.localdate().isoformat(),
                'nome': 'João Candidato',
                'funcoes': [self.cargo.pk],
                'telefone': '(11) 99999-9999',
                'email': 'joao@example.com',
                'endereco': 'Rua Teste',
                'cat_cnh': 'B',
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

    def test_salva_multiplas_funcoes_e_mantem_funcao_principal(self):
        segundo_cargo = Cargo.objects.create(empresa=self.empresa, nome='Motorista')
        form = CurriculoForm(
            data={
                'data': timezone.localdate().isoformat(),
                'nome': 'Maria Candidata',
                'funcoes': [self.cargo.pk, segundo_cargo.pk],
                'telefone': '',
                'email': '',
                'endereco': '',
                'cat_cnh': 'D',
                'indicacao': '',
                'status': 'novo',
                'observacoes': '',
            },
            empresa_ativa=self.empresa,
        )

        self.assertTrue(form.is_valid(), form.errors)
        curriculo = form.save(commit=False)
        curriculo.empresa = self.empresa
        curriculo.save()
        form.save_m2m()
        curriculo = Curriculo.objects.prefetch_related('funcoes').get(pk=curriculo.pk)

        self.assertEqual(curriculo.funcao, self.cargo)
        self.assertEqual(list(curriculo.funcoes.order_by('nome')), [segundo_cargo, self.cargo])
        self.assertEqual(curriculo.cat_cnh, 'D')
