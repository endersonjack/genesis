from django import forms

from .models import Local


class LocalForm(forms.ModelForm):
    class Meta:
        model = Local
        fields = ('nome', 'endereco', 'link_maps')
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
        }
