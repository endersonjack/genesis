from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw, ImageOps
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Flowable


def _iniciais_nome(nome: str | None) -> str:
    partes = (nome or '').split()
    return ''.join(parte[0] for parte in partes[:2]).upper() or 'F'


def _foto_funcionario_png(funcionario, *, px: int = 128) -> bytes | None:
    foto = getattr(funcionario, 'foto', None)
    if not foto:
        return None
    try:
        with foto.open('rb') as f:
            raw = f.read()
    except Exception:
        return None

    try:
        img = Image.open(BytesIO(raw))
        img = ImageOps.exif_transpose(img).convert('RGBA')
        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        img = img.crop((left, top, left + side, top + side)).resize(
            (px, px),
            Image.Resampling.LANCZOS,
        )
        mask = Image.new('L', (px, px), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, px - 1, px - 1), fill=255)
        img.putalpha(mask)
        out = BytesIO()
        img.save(out, format='PNG')
        return out.getvalue()
    except Exception:
        return None


class AvatarFuncionario(Flowable):
    def __init__(self, funcionario, size: float, *, initials: str | None = None):
        super().__init__()
        self.width = size
        self.height = size
        self.size = size
        self.initials = initials or _iniciais_nome(getattr(funcionario, 'nome', None))
        self.image_data = _foto_funcionario_png(funcionario)

    def draw(self):
        c = self.canv
        c.saveState()
        if self.image_data:
            c.drawImage(
                ImageReader(BytesIO(self.image_data)),
                0,
                0,
                width=self.size,
                height=self.size,
                mask='auto',
            )
        else:
            c.setFillColor(colors.HexColor('#e0f2fe'))
            c.circle(self.size / 2, self.size / 2, self.size / 2, fill=1, stroke=0)
            c.setFillColor(colors.HexColor('#075985'))
            c.setFont('Helvetica-Bold', max(5, self.size * 0.32))
            c.drawCentredString(self.size / 2, self.size * 0.36, self.initials[:2])
        c.setStrokeColor(colors.HexColor('#cbd5e1'))
        c.setLineWidth(0.45)
        c.circle(self.size / 2, self.size / 2, self.size / 2 - 0.25, fill=0, stroke=1)
        c.restoreState()
