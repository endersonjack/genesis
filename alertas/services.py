from django.contrib.contenttypes.models import ContentType

from .models import Alerta


def criar_ou_atualizar_alerta(
    *,
    empresa,
    titulo,
    descricao='',
    modulo=Alerta.Modulo.GERAL,
    categoria='',
    nivel=Alerta.Nivel.ATENCAO,
    data_alerta=None,
    data_vencimento=None,
    link_url='',
    usuario=None,
    objeto_origem=None,
    chave='',
    criado_por=None,
):
    """
    Ponto único para módulos criarem alertas idempotentes.

    Use `chave` para alertas automáticos que devem ser atualizados em vez de duplicados,
    por exemplo: `rh:contrato-vencendo:funcionario:123`.
    """
    defaults = {
        'usuario': usuario,
        'titulo': titulo,
        'descricao': descricao,
        'modulo': modulo,
        'categoria': categoria,
        'nivel': nivel,
        'data_vencimento': data_vencimento,
        'link_url': link_url,
        'criado_por': criado_por,
    }
    if data_alerta is not None:
        defaults['data_alerta'] = data_alerta
    if objeto_origem is not None:
        defaults['content_type'] = ContentType.objects.get_for_model(
            objeto_origem,
            for_concrete_model=False,
        )
        defaults['object_id'] = objeto_origem.pk

    if chave:
        alerta, _created = Alerta.objects.update_or_create(
            empresa=empresa,
            chave=chave,
            defaults=defaults,
        )
        return alerta

    return Alerta.objects.create(empresa=empresa, **defaults)
