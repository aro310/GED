from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model
from .models import Document

CustomUser = get_user_model()


class ImageUploadForm(forms.Form):
    image = forms.ImageField(label="Image à scanner (JPG, PNG...)")
    type_document = forms.ChoiceField(
        choices=Document.TYPE_CHOICES,
        label="Type de document"
    )
    convertir_en_pdf = forms.BooleanField(
        label="Convertir en PDF",
        required=False,
        initial=True
    )


    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Récupère l'utilisateur si fourni
        super().__init__(*args, **kwargs)

        # Si l'utilisateur est un étudiant, on retire le champ "etudiant"
        if user and user.groups.filter(name='Étudiants').exists():
            self.fields.pop('etudiant')


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom d’utilisateur'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mot de passe'})
    )

    class Meta:
        fields = ['username', 'password']


class CustomUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(choices=CustomUser.ROLE_CHOICES)

    class Meta:
        model = CustomUser
        fields = ('username', 'password1', 'password2', 'role', 'email')  # Inclut 'email' si nécessaire

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for fieldname in ['username', 'password1', 'password2', 'role', 'email']:
            if fieldname in self.fields:
                self.fields[fieldname].help_text = None

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data['role']
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'role']
