from django.urls import path
from .views import *

app_name = 'rh'

urlpatterns = [

    # ======================
    # DASHBOARD RH
    # ======================
    path('', dashboard_rh, name='dashboard_rh'),

    # ======================
    # FUNCIONÁRIOS - CRUD PRINCIPAL
    # ======================
    path('funcionarios/', lista_funcionarios, name='lista_funcionarios'),
    path('funcionarios/buscar/', buscar_funcionarios, name='buscar_funcionarios'),
    path('funcionarios/modal/novo-rapido/', modal_novo_funcionario_rapido, name='modal_novo_funcionario_rapido'),
    path('funcionarios/<int:pk>/', detalhar_funcionario, name='detalhes_funcionario'),
    path('funcionarios/<int:pk>/editar/', editar_funcionario, name='editar_funcionario'),
    path('funcionarios/<int:pk>/excluir/', excluir_funcionario, name='excluir_funcionario'),

    # ======================
    # CALENDÁRIO E LEMBRETES
    # ======================
    path('calendario/', calendario_rh, name='calendario_rh'),
    path('lembretes/', lista_lembretes_rh, name='lista_lembretes_rh'),
    path('lembretes/novo/', criar_lembrete_rh, name='criar_lembrete_rh'),
    path('lembretes/<int:pk>/editar/', editar_lembrete_rh, name='editar_lembrete_rh'),
    path('lembretes/<int:pk>/excluir/', excluir_lembrete_rh, name='excluir_lembrete_rh'),

    # ======================
    # CARGOS
    # ======================
    path('cargos/', lista_cargos, name='lista_cargos'),
    path('cargos/novo/', criar_cargo, name='criar_cargo'),
    path('cargos/<int:pk>/editar/', editar_cargo, name='editar_cargo'),
    path('cargos/<int:pk>/excluir/', excluir_cargo, name='excluir_cargo'),

    # ======================
    # LOTAÇÕES
    # ======================
    path('lotacoes/', lista_lotacoes, name='lista_lotacoes'),
    path('lotacoes/nova/', criar_lotacao, name='criar_lotacao'),
    path('lotacoes/<int:pk>/editar/', editar_lotacao, name='editar_lotacao'),
    path('lotacoes/<int:pk>/excluir/', excluir_lotacao, name='excluir_lotacao'),

    # ======================
    # MODAIS - DADOS PRINCIPAIS DO FUNCIONÁRIO
    # ======================
    path('funcionarios/<int:pk>/modal/editar-pessoais/', modal_editar_pessoais, name='modal_editar_pessoais'),
    path('funcionarios/<int:pk>/modal/editar-admissao/', modal_editar_admissao, name='modal_editar_admissao'),
    path('funcionarios/<int:pk>/modal/demissao/', modal_editar_demissao, name='modal_editar_demissao'),
    path('funcionarios/<int:pk>/modal/editar-bancarios/', modal_editar_bancarios, name='modal_editar_bancarios'),
    path('funcionarios/<int:pk>/modal/editar-outros/', modal_editar_outros, name='modal_editar_outros'),

    # ======================
    # FÉRIAS
    # ======================
    path('funcionarios/<int:pk>/ferias/lista/', ferias_lista, name='ferias_lista'),
    path('funcionarios/<int:pk>/modal/ferias/adicionar/', modal_adicionar_ferias, name='modal_adicionar_ferias'),
    path('funcionarios/<int:pk>/modal/ferias/<int:ferias_id>/editar/', modal_editar_ferias, name='modal_editar_ferias'),
    path('funcionarios/<int:pk>/modal/ferias/<int:ferias_id>/excluir/', modal_excluir_ferias, name='modal_excluir_ferias'),

    # ======================
    # AFASTAMENTOS
    # ======================
    path('funcionarios/<int:pk>/afastamentos/lista/', afastamentos_lista, name='afastamentos_lista'),
    path('funcionarios/<int:pk>/modal/afastamentos/adicionar/', modal_adicionar_afastamento, name='modal_adicionar_afastamento'),
    path('funcionarios/<int:pk>/modal/afastamentos/<int:afastamento_id>/editar/', modal_editar_afastamento, name='modal_editar_afastamento'),
    path('funcionarios/<int:pk>/modal/afastamentos/<int:afastamento_id>/excluir/', modal_excluir_afastamento, name='modal_excluir_afastamento'),

    # ======================
    # DEPENDENTES
    # ======================
    path('funcionarios/<int:pk>/dependentes/lista/', dependentes_lista, name='dependentes_lista'),
    path('funcionarios/<int:pk>/modal/dependentes/adicionar/', modal_adicionar_dependente, name='modal_adicionar_dependente'),
    path('funcionarios/<int:pk>/modal/dependentes/<int:dependente_id>/editar/', modal_editar_dependente, name='modal_editar_dependente'),
    path('funcionarios/<int:pk>/modal/dependentes/<int:dependente_id>/excluir/', modal_excluir_dependente, name='modal_excluir_dependente'),

    # ======================
    # SAÚDE - ASO
    # ======================
    path('funcionarios/<int:pk>/saude/aso/lista/', aso_lista, name='aso_lista'),
    path('funcionarios/<int:pk>/modal/saude/aso/adicionar/', modal_adicionar_aso, name='modal_adicionar_aso'),
    path('funcionarios/<int:pk>/modal/saude/aso/<int:aso_id>/editar/', modal_editar_aso, name='modal_editar_aso'),
    path('funcionarios/<int:pk>/modal/saude/aso/<int:aso_id>/excluir/', modal_excluir_aso, name='modal_excluir_aso'),

    # ======================
    # SAÚDE - CERTIFICADOS
    # ======================
    path('funcionarios/<int:pk>/saude/certificados/lista/', certificados_lista, name='certificados_lista'),
    path('funcionarios/<int:pk>/modal/saude/certificados/adicionar/', modal_adicionar_certificado, name='modal_adicionar_certificado'),
    path('funcionarios/<int:pk>/modal/saude/certificados/<int:certificado_id>/editar/', modal_editar_certificado, name='modal_editar_certificado'),
    path('funcionarios/<int:pk>/modal/saude/certificados/<int:certificado_id>/excluir/', modal_excluir_certificado, name='modal_excluir_certificado'),

    # ======================
    # SAÚDE - PCMSO
    # ======================
    path('funcionarios/<int:pk>/saude/pcmso/lista/', pcmso_lista, name='pcmso_lista'),
    path('funcionarios/<int:pk>/modal/saude/pcmso/adicionar/', modal_adicionar_pcmso, name='modal_adicionar_pcmso'),
    path('funcionarios/<int:pk>/modal/saude/pcmso/<int:pcmso_id>/editar/', modal_editar_pcmso, name='modal_editar_pcmso'),
    path('funcionarios/<int:pk>/modal/saude/pcmso/<int:pcmso_id>/excluir/', modal_excluir_pcmso, name='modal_excluir_pcmso'),

    # ======================
    # SAÚDE - ATESTADOS / LICENÇAS
    # ======================
    path('funcionarios/<int:pk>/saude/atestados-licencas/lista/', atestados_licencas_lista, name='atestados_licencas_lista'),
    path('funcionarios/<int:pk>/modal/saude/atestados-licencas/adicionar/', modal_adicionar_atestado_licenca, name='modal_adicionar_atestado_licenca'),
    path('funcionarios/<int:pk>/modal/saude/atestados-licencas/<int:atestado_id>/editar/', modal_editar_atestado_licenca, name='modal_editar_atestado_licenca'),
    path('funcionarios/<int:pk>/modal/saude/atestados-licencas/<int:atestado_id>/excluir/', modal_excluir_atestado_licenca, name='modal_excluir_atestado_licenca'),

    # ======================
    # SAÚDE - OCORRÊNCIAS
    # ======================
    path('funcionarios/<int:pk>/saude/ocorrencias/lista/', ocorrencias_saude_lista, name='ocorrencias_saude_lista'),
    path('funcionarios/<int:pk>/modal/saude/ocorrencias/adicionar/', modal_adicionar_ocorrencia_saude, name='modal_adicionar_ocorrencia_saude'),
    path('funcionarios/<int:pk>/modal/saude/ocorrencias/<int:ocorrencia_id>/editar/', modal_editar_ocorrencia_saude, name='modal_editar_ocorrencia_saude'),
    path('funcionarios/<int:pk>/modal/saude/ocorrencias/<int:ocorrencia_id>/excluir/', modal_excluir_ocorrencia_saude, name='modal_excluir_ocorrencia_saude'),

    # ======================
    # ANEXOS AVULSOS
    # ======================
    path('funcionarios/<int:pk>/anexos-avulsos/lista/', anexos_avulsos_lista, name='anexos_avulsos_lista'),
    path('funcionarios/<int:pk>/modal/anexos-avulsos/adicionar/', modal_adicionar_anexo_avulso, name='modal_adicionar_anexo_avulso'),
    path('funcionarios/<int:pk>/modal/anexos-avulsos/<int:anexo_id>/editar/', modal_editar_anexo_avulso, name='modal_editar_anexo_avulso'),
    path('funcionarios/<int:pk>/modal/anexos-avulsos/<int:anexo_id>/excluir/', modal_excluir_anexo_avulso, name='modal_excluir_anexo_avulso'),
]