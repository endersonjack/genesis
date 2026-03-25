from django.urls import path
from . import views

app_name = 'rh'

urlpatterns = [
    path('', views.dashboard_rh, name='dashboard_rh'),
    path('funcionarios/', views.lista_funcionarios, name='lista_funcionarios'),
    path(
    'funcionarios/modal/novo-rapido/',
    views.modal_novo_funcionario_rapido,
    name='modal_novo_funcionario_rapido'
),
    path('funcionarios/<int:pk>/', views.detalhar_funcionario, name='detalhes_funcionario'),
    path('funcionarios/<int:pk>/editar/', views.editar_funcionario, name='editar_funcionario'),
    path('funcionarios/<int:pk>/excluir/', views.excluir_funcionario, name='excluir_funcionario'),


    path('funcionarios/buscar/', views.buscar_funcionarios, name='buscar_funcionarios'),

    path('calendario/', views.calendario_rh, name='calendario_rh'),
    path('lembretes/', views.lista_lembretes_rh, name='lista_lembretes_rh'),
    path('lembretes/novo/', views.criar_lembrete_rh, name='criar_lembrete_rh'),
    path('lembretes/<int:pk>/editar/', views.editar_lembrete_rh, name='editar_lembrete_rh'),
    path('lembretes/<int:pk>/excluir/', views.excluir_lembrete_rh, name='excluir_lembrete_rh'),


    path('cargos/', views.lista_cargos, name='lista_cargos'),
    path('cargos/novo/', views.criar_cargo, name='criar_cargo'),
    path('cargos/<int:pk>/editar/', views.editar_cargo, name='editar_cargo'),
    path('cargos/<int:pk>/excluir/', views.excluir_cargo, name='excluir_cargo'),

    path('lotacoes/', views.lista_lotacoes, name='lista_lotacoes'),
    path('lotacoes/nova/', views.criar_lotacao, name='criar_lotacao'),
    path('lotacoes/<int:pk>/editar/', views.editar_lotacao, name='editar_lotacao'),
    path('lotacoes/<int:pk>/excluir/', views.excluir_lotacao, name='excluir_lotacao'),

    path('funcionarios/<int:pk>/modal/editar-pessoais/',views.modal_editar_pessoais,name="modal_editar_pessoais",),
    path("funcionarios/<int:pk>/modal/editar-admissao/", views.modal_editar_admissao, name="modal_editar_admissao",),
    path("funcionarios/<int:pk>/modal/demissao/",views.modal_editar_demissao,name="modal_editar_demissao"),
    path("funcionarios/<int:pk>/modal/editar-bancarios/", views.modal_editar_bancarios,name="modal_editar_bancarios",),
    path("funcionarios/<int:pk>/modal/editar-outros/",views.modal_editar_outros,name="modal_editar_outros",),

    path(
    "funcionarios/<int:pk>/ferias/lista/",
    views.ferias_lista,
    name="ferias_lista",
    ),
    path(
        "funcionarios/<int:pk>/modal/ferias/adicionar/",
        views.modal_adicionar_ferias,
        name="modal_adicionar_ferias",
    ),
    path(
        "funcionarios/<int:pk>/modal/ferias/<int:ferias_id>/editar/",
        views.modal_editar_ferias,
        name="modal_editar_ferias",
    ),
    path(
        "funcionarios/<int:pk>/modal/ferias/<int:ferias_id>/excluir/",
        views.modal_excluir_ferias,
        name="modal_excluir_ferias",
    ),

    path(
    "funcionarios/<int:pk>/afastamentos/lista/",
    views.afastamentos_lista,
    name="afastamentos_lista",
    ),
    path(
        "funcionarios/<int:pk>/modal/afastamentos/adicionar/",
        views.modal_adicionar_afastamento,
        name="modal_adicionar_afastamento",
    ),
    path(
        "funcionarios/<int:pk>/modal/afastamentos/<int:afastamento_id>/editar/",
        views.modal_editar_afastamento,
        name="modal_editar_afastamento",
    ),
    path(
        "funcionarios/<int:pk>/modal/afastamentos/<int:afastamento_id>/excluir/",
        views.modal_excluir_afastamento,
        name="modal_excluir_afastamento",
    ),

    path(
    "funcionarios/<int:pk>/dependentes/lista/",
    views.dependentes_lista,
    name="dependentes_lista",
),
path(
    "funcionarios/<int:pk>/modal/dependentes/adicionar/",
    views.modal_adicionar_dependente,
    name="modal_adicionar_dependente",
),
path(
    "funcionarios/<int:pk>/modal/dependentes/<int:dependente_id>/editar/",
    views.modal_editar_dependente,
    name="modal_editar_dependente",
),
path(
    "funcionarios/<int:pk>/modal/dependentes/<int:dependente_id>/excluir/",
    views.modal_excluir_dependente,
    name="modal_excluir_dependente",
),

path(
    "funcionarios/<int:pk>/saude/aso/lista/",
    views.aso_lista,
    name="aso_lista",
),
path(
    "funcionarios/<int:pk>/modal/saude/aso/adicionar/",
    views.modal_adicionar_aso,
    name="modal_adicionar_aso",
),
path(
    "funcionarios/<int:pk>/modal/saude/aso/<int:aso_id>/editar/",
    views.modal_editar_aso,
    name="modal_editar_aso",
),
path(
    "funcionarios/<int:pk>/modal/saude/aso/<int:aso_id>/excluir/",
    views.modal_excluir_aso,
    name="modal_excluir_aso",
),

path(
    "funcionarios/<int:pk>/saude/certificados/lista/",
    views.certificados_lista,
    name="certificados_lista",
),
path(
    "funcionarios/<int:pk>/modal/saude/certificados/adicionar/",
    views.modal_adicionar_certificado,
    name="modal_adicionar_certificado",
),
path(
    "funcionarios/<int:pk>/modal/saude/certificados/<int:certificado_id>/editar/",
    views.modal_editar_certificado,
    name="modal_editar_certificado",
),
path(
    "funcionarios/<int:pk>/modal/saude/certificados/<int:certificado_id>/excluir/",
    views.modal_excluir_certificado,
    name="modal_excluir_certificado",
),


path(
    "funcionarios/<int:pk>/saude/pcmso/lista/",
    views.pcmso_lista,
    name="pcmso_lista",
),
path(
    "funcionarios/<int:pk>/modal/saude/pcmso/adicionar/",
    views.modal_adicionar_pcmso,
    name="modal_adicionar_pcmso",
),
path(
    "funcionarios/<int:pk>/modal/saude/pcmso/<int:pcmso_id>/editar/",
    views.modal_editar_pcmso,
    name="modal_editar_pcmso",
),
path(
    "funcionarios/<int:pk>/modal/saude/pcmso/<int:pcmso_id>/excluir/",
    views.modal_excluir_pcmso,
    name="modal_excluir_pcmso",
),

path(
    "funcionarios/<int:pk>/saude/atestados-licencas/lista/",
    views.atestados_licencas_lista,
    name="atestados_licencas_lista",
),
path(
    "funcionarios/<int:pk>/modal/saude/atestados-licencas/adicionar/",
    views.modal_adicionar_atestado_licenca,
    name="modal_adicionar_atestado_licenca",
),
path(
    "funcionarios/<int:pk>/modal/saude/atestados-licencas/<int:atestado_id>/editar/",
    views.modal_editar_atestado_licenca,
    name="modal_editar_atestado_licenca",
),
path(
    "funcionarios/<int:pk>/modal/saude/atestados-licencas/<int:atestado_id>/excluir/",
    views.modal_excluir_atestado_licenca,
    name="modal_excluir_atestado_licenca",
),


path(
    "funcionarios/<int:pk>/saude/ocorrencias/lista/",
    views.ocorrencias_saude_lista,
    name="ocorrencias_saude_lista",
),
path(
    "funcionarios/<int:pk>/modal/saude/ocorrencias/adicionar/",
    views.modal_adicionar_ocorrencia_saude,
    name="modal_adicionar_ocorrencia_saude",
),
path(
    "funcionarios/<int:pk>/modal/saude/ocorrencias/<int:ocorrencia_id>/editar/",
    views.modal_editar_ocorrencia_saude,
    name="modal_editar_ocorrencia_saude",
),
path(
    "funcionarios/<int:pk>/modal/saude/ocorrencias/<int:ocorrencia_id>/excluir/",
    views.modal_excluir_ocorrencia_saude,
    name="modal_excluir_ocorrencia_saude",
),

path(
    "funcionarios/<int:pk>/anexos-avulsos/lista/",
    views.anexos_avulsos_lista,
    name="anexos_avulsos_lista",
),
path(
    "funcionarios/<int:pk>/modal/anexos-avulsos/adicionar/",
    views.modal_adicionar_anexo_avulso,
    name="modal_adicionar_anexo_avulso",
),
path(
    "funcionarios/<int:pk>/modal/anexos-avulsos/<int:anexo_id>/editar/",
    views.modal_editar_anexo_avulso,
    name="modal_editar_anexo_avulso",
),
path(
    "funcionarios/<int:pk>/modal/anexos-avulsos/<int:anexo_id>/excluir/",
    views.modal_excluir_anexo_avulso,
    name="modal_excluir_anexo_avulso",
),

]