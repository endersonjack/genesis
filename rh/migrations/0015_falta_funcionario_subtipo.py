from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0014_falta_funcionario'),
    ]

    operations = [
        migrations.AddField(
            model_name='faltafuncionario',
            name='subtipo',
            field=models.CharField(
                blank=True,
                choices=[
                    ('ab_falecimento', 'Falecimento'),
                    ('ab_casamento', 'Casamento'),
                    ('ab_nascimento_filho', 'Nascimento de filho (licença-paternidade)'),
                    ('ab_doacao_sangue', 'Doação voluntária de sangue'),
                    ('ab_alistamento_eleitoral', 'Alistamento eleitoral'),
                    ('ab_servico_militar', 'Exigências do serviço militar'),
                    ('ab_vestibular', 'Prova de vestibular'),
                    ('ab_juizo', 'Comparecimento em juízo'),
                    ('ab_representacao_sindical', 'Representação sindical (reunião oficial)'),
                    ('ab_acompanhar_gestante', 'Acompanhar esposa/companheira gestante'),
                    ('ab_acompanhar_filho', 'Acompanhar filho (consulta)'),
                    ('ab_exames_cancer', 'Exames preventivos de câncer'),
                    ('ab_outro', 'Outro'),
                    ('sa_atestado', 'Atestado médico/odontológico'),
                    ('sa_acidente_doenca', 'Acidente de trabalho / doença'),
                    ('sa_outro', 'Outro'),
                    ('nj_falta_injustificada', 'Falta injustificada'),
                    ('nj_atraso', 'Atraso'),
                    ('nj_saida_antecipada', 'Saída antecipada'),
                    ('nj_ausencia_parcial', 'Ausência parcial'),
                    ('nj_outro', 'Outro'),
                ],
                max_length=40,
            ),
        ),
    ]

