import uuid
from pathlib import Path


def item_imagem_upload(instance, filename):
    ext = Path(filename).suffix[:10] or '.jpg'
    return f'estoque/itens/{instance.item_id}/img/{uuid.uuid4().hex}{ext}'


def item_qrcode_upload(instance, filename):
    ext = Path(filename).suffix[:10] or '.png'
    return f'estoque/itens/{instance.pk}/qrcode{ext}'
