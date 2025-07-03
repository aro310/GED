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
        label="Transformer en PDF",
        required=False,
        initial=True
    )
    convertir_en_audio = forms.BooleanField(
        label="Convertir en audio",
        required=False,
        initial=True
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Récupère l'utilisateur si fourni
        super().__init__(*args, **kwargs)

        # Si l'utilisateur est un étudiant, on retire le champ "etudiant"
        if user and user.groups.filter(name='Étudiants').exists():
            self.fields.pop('etudiant', None)

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom d’utilisateur'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mot de passe'})
    )

    class Meta:
        fields = ['username', 'password']


CustomUser = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(choices=CustomUser.ROLE_CHOICES)
    photo = forms.ImageField(required=False, label="Photo de profil")

    class Meta:
        model = CustomUser
        fields = ('username', 'password1', 'password2', 'role', 'email', 'photo')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for fieldname in ['username', 'password1', 'password2', 'role', 'email']:
            if fieldname in self.fields:
                self.fields[fieldname].help_text = None

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo:
            valid_extensions = ['jpg', 'jpeg', 'png']
            extension = photo.name.split('.')[-1].lower()
            if extension not in valid_extensions:
                raise forms.ValidationError("L'image doit être au format JPG ou PNG.")
            if photo.size > 5 * 1024 * 1024:  # 5 Mo
                raise forms.ValidationError("L'image ne doit pas dépasser 5 Mo.")
        return photo

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data['role']
        photo = self.cleaned_data.get('photo')
        print("Photo reçue dans cleaned_data:", photo)  # Débogage
        user.photo = photo
        if commit:
            user.save()
        return user

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'role','photo']
