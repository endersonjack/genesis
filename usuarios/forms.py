from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

Usuario = get_user_model()


class MeuPerfilForm(forms.ModelForm):
    nova_senha = forms.CharField(
        label='Nova senha',
        required=False,
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'autocomplete': 'new-password',
                'placeholder': 'Deixe em branco para não alterar',
            }
        ),
    )
    nova_senha_confirmar = forms.CharField(
        label='Confirmar nova senha',
        required=False,
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'autocomplete': 'new-password',
                'placeholder': 'Repita a nova senha',
            }
        ),
    )

    class Meta:
        model = Usuario
        fields = ('nome_completo', 'username', 'foto')
        widgets = {
            'nome_completo': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Seu nome para exibição'}
            ),
            'username': forms.TextInput(
                attrs={'class': 'form-control', 'autocomplete': 'username'}
            ),
            'foto': forms.ClearableFileInput(
                attrs={
                    'class': 'form-control',
                    'accept': 'image/*',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome_completo'].required = False
        self.fields['foto'].required = False
        self.fields['username'].help_text = (
            'Letras, números e @ . + - _ (máx. 150 caracteres). Usado para entrar no sistema.'
        )

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise ValidationError('Informe um nome de usuário (login).')
        qs = Usuario.objects.filter(username=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Já existe um usuário com este login.')
        return username

    def clean(self):
        data = super().clean()
        p1 = data.get('nova_senha') or ''
        p2 = data.get('nova_senha_confirmar') or ''
        if p1 or p2:
            if p1 != p2:
                raise ValidationError('A confirmação da senha não confere.')
            if p1:
                validate_password(p1, user=self.instance)
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        nova = self.cleaned_data.get('nova_senha')
        if nova:
            user.set_password(nova)
        if commit:
            user.save()
        return user
