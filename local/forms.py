import re

from django import forms
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

from .models import Local


class LocalForm(forms.ModelForm):
    # Override do campo do model (URLField) para permitir colar o <iframe ...> completo.
    link_maps_embed = forms.CharField(
        required=False,
        label='Link embed (iframe)',
        help_text='Cole aqui o link do atributo src do iframe do Google Maps.',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'https://www.google.com/maps/embed?pb=... (ou cole o <iframe ...>)',
                'maxlength': '2000',
            }
        ),
    )

    obter_lat_lng_do_maps = forms.BooleanField(
        required=False,
        initial=True,
        label='Preencher latitude/longitude pelo link do Maps',
        help_text='Se o link tiver coordenadas, o sistema tenta extrair e preencher automaticamente.',
    )

    class Meta:
        model = Local
        fields = ('nome', 'endereco', 'link_maps', 'link_maps_embed', 'latitude', 'longitude')
        widgets = {
            'nome': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'autocomplete': 'organization',
                    'maxlength': '150',
                }
            ),
            'endereco': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'autocomplete': 'street-address',
                    'maxlength': '500',
                }
            ),
            'link_maps': forms.URLInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'https://maps.google.com/...',
                    'maxlength': '2000',
                }
            ),
            'latitude': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': '',
                    'step': 'any',
                    'inputmode': 'decimal',
                }
            ),
            'longitude': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': '',
                    'step': 'any',
                    'inputmode': 'decimal',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Garante o padrão marcado no GET (no POST, o valor vem do usuário).
        self.fields['obter_lat_lng_do_maps'].initial = True

    def clean_link_maps_embed(self):
        raw = (self.cleaned_data.get('link_maps_embed') or '').strip()
        if not raw:
            return raw

        # Aceita colar o iframe completo: extrai o src.
        if '<iframe' in raw.lower():
            m = re.search(r'\bsrc\s*=\s*"([^"]+)"', raw, flags=re.IGNORECASE)
            if not m:
                m = re.search(r"\bsrc\s*=\s*'([^']+)'", raw, flags=re.IGNORECASE)
            if m:
                return (m.group(1) or '').strip()

        url = raw
        v = URLValidator()
        try:
            v(url)
        except ValidationError:
            raise forms.ValidationError('Informe uma URL válida (ou cole um iframe com src válido).')

        return url

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('obter_lat_lng_do_maps'):
            # Permite salvar tudo vazio (embed e coordenadas), sem erro.
            src = (cleaned.get('link_maps_embed') or '').strip()
            if not src:
                return cleaned
            lat, lng = Local.parse_lat_lng_from_maps(src)
            if lat is not None and lng is not None:
                cleaned['latitude'] = lat
                cleaned['longitude'] = lng
            else:
                self.add_error(
                    'link_maps_embed',
                    'Não consegui extrair latitude/longitude do link embed. Preencha manualmente ou use um embed que contenha coordenadas (ex.: iframe com “!2d…!3d…”).',
                )
        return cleaned
