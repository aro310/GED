from django import forms
from .models import Etudiant, Document

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