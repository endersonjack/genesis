from rh.models import HistoricoAlteracao, Funcionario


def registrar_alteracao_situacao(funcionario, usuario, situacao_antiga, situacao_nova):
    if str(situacao_antiga or "") == str(situacao_nova or ""):
        return

    # usa os choices corretos
    mapa = dict(Funcionario.STATUS_CHOICES)

    HistoricoAlteracao.objects.create(
        funcionario=funcionario,
        usuario=usuario if getattr(usuario, "is_authenticated", False) else None,
        acao="update",
        modelo="Funcionario",
        registro_id=str(funcionario.pk),
        titulo="Alteração de situação",
        # descricao="A situação do funcionário foi alterada.",
        alteracoes={
            "situacao": {
                "label": "Situação",
                "de": mapa.get(situacao_antiga, str(situacao_antiga or "—")),
                "para": mapa.get(situacao_nova, str(situacao_nova or "—")),
            }
        }
    )