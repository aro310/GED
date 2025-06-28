from django import forms
from .models import Etudiant, Document
from django.contrib.auth.forms import AuthenticationForm,UserCreationForm
from django.contrib.auth import get_user_model

class ImageUploadForm(forms.Form):
    image = forms.ImageField(label="Image à scanner (JPG, PNG...)")
    etudiant = forms.ModelChoiceField(
        queryset=Etudiant.objects.all(),
        required=False,
        label="Associer à un étudiant (facultatif)"
    )
    type_document = forms.ChoiceField(
        choices=Document.TYPE_CHOICES,
        label="Type de document"
    )

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

    class Meta:
        model = CustomUser
        fields = ('username', 'password1', 'password2', 'role', 'email')  # Ajoutez 'email' si utilisé

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for fieldname in ['username', 'password1', 'password2', 'role', 'email']:
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