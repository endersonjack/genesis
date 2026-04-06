from django.urls import path

from core.view_helpers import empresa_scoped

from .views import *

app_name = 'rh'

urlpatterns = [

    # ======================
    # DASHBOARD RH
    # ======================
    path('', empresa_scoped(dashboard_rh), name='dashboard_rh'),

    # ======================
    # FUNCIONÁRIOS - CRUD PRINCIPAL
    # ======================
    path('funcionarios/', empresa_scoped(lista_funcionarios), name='lista_funcionarios'),
    path('funcionarios/buscar/', empresa_scoped(buscar_funcionarios), name='buscar_funcionarios'),
    path('funcionarios/modal/novo-rapido/', empresa_scoped(modal_novo_funcionario_rapido), name='modal_novo_funcionario_rapido'),
    path('funcionarios/<int:pk>/', empresa_scoped(detalhar_funcionario), name='detalhes_funcionario'),
    path('funcionarios/<int:pk>/editar/', empresa_scoped(editar_funcionario), name='editar_funcionario'),
    path('funcionarios/<int:pk>/excluir/', empresa_scoped(excluir_funcionario), name='excluir_funcionario'),

    # ======================
    # CALENDÁRIO E LEMBRETES
    # ======================
    path('calendario/', empresa_scoped(calendario_rh), name='calendario_rh'),
    path('lembretes/', empresa_scoped(lista_lembretes_rh), name='lista_lembretes_rh'),
    path('lembretes/novo/', empresa_scoped(criar_lembrete_rh), name='criar_lembrete_rh'),
    path('lembretes/<int:pk>/editar/', empresa_scoped(editar_lembrete_rh), name='editar_lembrete_rh'),
    path('lembretes/<int:pk>/excluir/', empresa_scoped(excluir_lembrete_rh), name='excluir_lembrete_rh'),

    # ======================
    # CARGOS
    # ======================
    path('cargos/', empresa_scoped(lista_cargos), name='lista_cargos'),
    path('cargos/novo/', empresa_scoped(criar_cargo), name='criar_cargo'),
    path('cargos/<int:pk>/editar/', empresa_scoped(editar_cargo), name='editar_cargo'),
    path('cargos/<int:pk>/excluir/', empresa_scoped(excluir_cargo), name='excluir_cargo'),

    # ======================
    # LOTAÇÕES
    # ======================
    path('lotacoes/', empresa_scoped(lista_lotacoes), name='lista_lotacoes'),
    path('lotacoes/nova/', empresa_scoped(criar_lotacao), name='criar_lotacao'),
    path('lotacoes/<int:pk>/editar/', empresa_scoped(editar_lotacao), name='editar_lotacao'),
    path('lotacoes/<int:pk>/excluir/', empresa_scoped(excluir_lotacao), name='excluir_lotacao'),

    # ======================
    # MODAIS - DADOS PRINCIPAIS DO FUNCIONÁRIO
    # ======================
    path('funcionarios/<int:pk>/modal/editar-pessoais/', empresa_scoped(modal_editar_pessoais), name='modal_editar_pessoais'),
    path('funcionarios/<int:pk>/modal/editar-admissao/', empresa_scoped(modal_editar_admissao), name='modal_editar_admissao'),
    path('funcionarios/<int:pk>/modal/demissao/', empresa_scoped(modal_editar_demissao), name='modal_editar_demissao'),
    path('funcionarios/<int:pk>/modal/editar-bancarios/', empresa_scoped(modal_editar_bancarios), name='modal_editar_bancarios'),
    path('funcionarios/<int:pk>/modal/editar-outros/', empresa_scoped(modal_editar_outros), name='modal_editar_outros'),

    # ======================
    # FÉRIAS
    # ======================
    path('funcionarios/<int:pk>/ferias/lista/', empresa_scoped(ferias_lista), name='ferias_lista'),
    path('funcionarios/<int:pk>/modal/ferias/adicionar/', empresa_scoped(modal_adicionar_ferias), name='modal_adicionar_ferias'),
    path('funcionarios/<int:pk>/modal/ferias/<int:ferias_id>/editar/', empresa_scoped(modal_editar_ferias), name='modal_editar_ferias'),
    path('funcionarios/<int:pk>/modal/ferias/<int:ferias_id>/excluir/', empresa_scoped(modal_excluir_ferias), name='modal_excluir_ferias'),

    # ======================
    # AFASTAMENTOS
    # ======================
    path('funcionarios/<int:pk>/afastamentos/lista/', empresa_scoped(afastamentos_lista), name='afastamentos_lista'),
    path('funcionarios/<int:pk>/modal/afastamentos/adicionar/', empresa_scoped(modal_adicionar_afastamento), name='modal_adicionar_afastamento'),
    path('funcionarios/<int:pk>/modal/afastamentos/<int:afastamento_id>/editar/', empresa_scoped(modal_editar_afastamento), name='modal_editar_afastamento'),
    path('funcionarios/<int:pk>/modal/afastamentos/<int:afastamento_id>/excluir/', empresa_scoped(modal_excluir_afastamento), name='modal_excluir_afastamento'),

    # ======================
    # DEPENDENTES
    # ======================
    path('funcionarios/<int:pk>/dependentes/lista/', empresa_scoped(dependentes_lista), name='dependentes_lista'),
    path('funcionarios/<int:pk>/modal/dependentes/adicionar/', empresa_scoped(modal_adicionar_dependente), name='modal_adicionar_dependente'),
    path('funcionarios/<int:pk>/modal/dependentes/<int:dependente_id>/editar/', empresa_scoped(modal_editar_dependente), name='modal_editar_dependente'),
    path('funcionarios/<int:pk>/modal/dependentes/<int:dependente_id>/excluir/', empresa_scoped(modal_excluir_dependente), name='modal_excluir_dependente'),

    # ======================
    # SAÚDE - ASO
    # ======================
    path('funcionarios/<int:pk>/saude/aso/lista/', empresa_scoped(aso_lista), name='aso_lista'),
    path('funcionarios/<int:pk>/modal/saude/aso/adicionar/', empresa_scoped(modal_adicionar_aso), name='modal_adicionar_aso'),
    path('funcionarios/<int:pk>/modal/saude/aso/<int:aso_id>/editar/', empresa_scoped(modal_editar_aso), name='modal_editar_aso'),
    path('funcionarios/<int:pk>/modal/saude/aso/<int:aso_id>/excluir/', empresa_scoped(modal_excluir_aso), name='modal_excluir_aso'),

    # ======================
    # SAÚDE - CERTIFICADOS
    # ======================
    path('funcionarios/<int:pk>/saude/certificados/lista/', empresa_scoped(certificados_lista), name='certificados_lista'),
    path('funcionarios/<int:pk>/modal/saude/certificados/adicionar/', empresa_scoped(modal_adicionar_certificado), name='modal_adicionar_certificado'),
    path('funcionarios/<int:pk>/modal/saude/certificados/<int:certificado_id>/editar/', empresa_scoped(modal_editar_certificado), name='modal_editar_certificado'),
    path('funcionarios/<int:pk>/modal/saude/certificados/<int:certificado_id>/excluir/', empresa_scoped(modal_excluir_certificado), name='modal_excluir_certificado'),

    # ======================
    # SAÚDE - PCMSO
    # ======================
    path('funcionarios/<int:pk>/saude/pcmso/lista/', empresa_scoped(pcmso_lista), name='pcmso_lista'),
    path('funcionarios/<int:pk>/modal/saude/pcmso/adicionar/', empresa_scoped(modal_adicionar_pcmso), name='modal_adicionar_pcmso'),
    path('funcionarios/<int:pk>/modal/saude/pcmso/<int:pcmso_id>/editar/', empresa_scoped(modal_editar_pcmso), name='modal_editar_pcmso'),
    path('funcionarios/<int:pk>/modal/saude/pcmso/<int:pcmso_id>/excluir/', empresa_scoped(modal_excluir_pcmso), name='modal_excluir_pcmso'),

    # ======================
    # SAÚDE - ATESTADOS / LICENÇAS
    # ======================
    path('funcionarios/<int:pk>/saude/atestados-licencas/lista/', empresa_scoped(atestados_licencas_lista), name='atestados_licencas_lista'),
    path('funcionarios/<int:pk>/modal/saude/atestados-licencas/adicionar/', empresa_scoped(modal_adicionar_atestado_licenca), name='modal_adicionar_atestado_licenca'),
    path('funcionarios/<int:pk>/modal/saude/atestados-licencas/<int:atestado_id>/editar/', empresa_scoped(modal_editar_atestado_licenca), name='modal_editar_atestado_licenca'),
    path('funcionarios/<int:pk>/modal/saude/atestados-licencas/<int:atestado_id>/excluir/', empresa_scoped(modal_excluir_atestado_licenca), name='modal_excluir_atestado_licenca'),

    # ======================
    # SAÚDE - OCORRÊNCIAS
    # ======================
    path('funcionarios/<int:pk>/saude/ocorrencias/lista/', empresa_scoped(ocorrencias_saude_lista), name='ocorrencias_saude_lista'),
    path('funcionarios/<int:pk>/modal/saude/ocorrencias/adicionar/', empresa_scoped(modal_adicionar_ocorrencia_saude), name='modal_adicionar_ocorrencia_saude'),
    path('funcionarios/<int:pk>/modal/saude/ocorrencias/<int:ocorrencia_id>/editar/', empresa_scoped(modal_editar_ocorrencia_saude), name='modal_editar_ocorrencia_saude'),
    path('funcionarios/<int:pk>/modal/saude/ocorrencias/<int:ocorrencia_id>/excluir/', empresa_scoped(modal_excluir_ocorrencia_saude), name='modal_excluir_ocorrencia_saude'),

    # ======================
    # ANEXOS AVULSOS
    # ======================
    path('funcionarios/<int:pk>/anexos-avulsos/lista/', empresa_scoped(anexos_avulsos_lista), name='anexos_avulsos_lista'),
    path('funcionarios/<int:pk>/modal/anexos-avulsos/adicionar/', empresa_scoped(modal_adicionar_anexo_avulso), name='modal_adicionar_anexo_avulso'),
    path('funcionarios/<int:pk>/modal/anexos-avulsos/<int:anexo_id>/editar/', empresa_scoped(modal_editar_anexo_avulso), name='modal_editar_anexo_avulso'),
    path('funcionarios/<int:pk>/modal/anexos-avulsos/<int:anexo_id>/excluir/', empresa_scoped(modal_excluir_anexo_avulso), name='modal_excluir_anexo_avulso'),
]
