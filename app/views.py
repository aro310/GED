import os
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.conf import settings
from .forms import ImageUploadForm, CustomLoginForm, CustomUserCreationForm
from .models import Document, CustomUser
from .ocr_utils import extraire_texte_depuis_image
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from io import BytesIO
import pytesseract
import traceback
from elevenlabs.client import ElevenLabs

# Configurer Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tessdata_dir_config = r'--tessdata-dir "C:\Program Files\Tesseract-OCR\tessdata"'

# Initialiser le client ElevenLabs
client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)

def upload_image(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            print("Données du formulaire :", form.cleaned_data)  # Débogage
            image = form.cleaned_data['image']
            image_path = os.path.join(settings.MEDIA_ROOT, 'temp', image.name)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)

            # Enregistrer l'image temporairement
            with open(image_path, 'wb+') as f:
                for chunk in image.chunks():
                    f.write(chunk)

            try:
                # Extraire le texte avec Tesseract
                with Image.open(image_path) as img:
                    texte = extraire_texte_depuis_image(image_path)

                # Vérifier si du texte a été extrait
                if not texte or texte.startswith("Erreur OCR"):
                    raise Exception("Aucun texte extrait ou erreur OCR")

                # Créer un PDF avec le texte extrait
                pdf_buffer = BytesIO()
                pdf = canvas.Canvas(pdf_buffer, pagesize=A4)
                pdf.setFont("Helvetica", 12)
                text_object = pdf.beginText(40, A4[1] - 40)  # Marge de 40 points
                for line in texte.split('\n'):
                    text_object.textLine(line)
                pdf.drawText(text_object)
                pdf.save()

                # Nom du fichier PDF
                pdf_name = image.name.rsplit('.', 1)[0] + '.pdf'
                pdf_path = os.path.join(settings.MEDIA_ROOT, 'documents', pdf_name)
                os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

                # Enregistrer le PDF sur le disque
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_buffer.getvalue())

                # Générer l'audio avec ElevenLabs
                audio_name = image.name.rsplit('.', 1)[0] + '.mp3'
                audio_path = os.path.join(settings.MEDIA_ROOT, 'audio', audio_name)
                os.makedirs(os.path.dirname(audio_path), exist_ok=True)

                audio = client.text_to_speech.convert(
                    text=texte,
                    voice_id="pNInz6obpgDQGcFmaJgB",
                    model_id="eleven_multilingual_v2",
                    output_format="mp3_44100_128",
                )

                # Enregistrer l'audio sur le disque
                with open(audio_path, 'wb') as f:
                    for chunk in audio:
                        f.write(chunk)

                # Enregistrer le document dans le modèle Document
                document = Document(
                    type_document=form.cleaned_data.get('type_document', 'autre'),
                    fichier=f'documents/{pdf_name}',
                    uploaded_by=request.user if request.user.is_authenticated else None,
                    etudiant=form.cleaned_data.get('etudiant')
                )
                document.save()

                # Fermer le buffer PDF
                pdf_buffer.close()

                # Supprimer le fichier temporaire
                try:
                    if os.path.exists(image_path):
                        os.remove(image_path)
                except PermissionError as e:
                    print(f"Impossible de supprimer le fichier temporaire : {e}")

                return render(request, 'app/resultat.html', {
                    'document': document,
                    'texte': texte,
                    'audio_url': f'{settings.MEDIA_URL}audio/{audio_name}'
                })
            except Exception as e:
                if os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except PermissionError:
                        print(f"Impossible de supprimer le fichier temporaire : {image_path}")
                print(traceback.format_exc())
                return render(request, 'app/resultat.html', {'texte': f"Erreur : {str(e)}"})
    else:
        form = ImageUploadForm()
    return render(request, 'app/upload.html', {'form': form})

def login_view(request):
    print(f"Utilisateur authentifié : {request.user.is_authenticated}")
    print(f"Utilisateur : {request.user}")
    print(f"Rôle : {getattr(request.user, 'role', 'Aucun rôle')}")
    print(f"CSRF Cookie : {request.META.get('CSRF_COOKIE')}")
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        print(f"Formulaire valide : {form.is_valid()}, Erreurs : {form.errors}")
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            print(f"Authentification pour {username} : {user is not None}")
            if user is not None:
                login(request, user)
                return redirect_by_role(user)
    else:
        form = CustomLoginForm()
    return render(request, 'app/login.html', {'form': form})

def register_view(request):
    """Vue pour l'inscription d'un nouvel utilisateur."""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Connecter l'utilisateur automatiquement après inscription
            login(request, user)
            return redirect_by_role(user)
    else:
        form = CustomUserCreationForm()
    return render(request, 'app/register.html', {'form': form})

def redirect_by_role(user):
    """Redirige l'utilisateur selon son rôle."""
    if user.role == 'admin':
        return redirect('admin_dashboard')  # URL pour le tableau de bord admin
    elif user.role == 'prof':
        return redirect('prof_dashboard')   # URL pour le tableau de bord prof
    elif user.role == 'secretariat':
        return redirect('secretariat_dashboard')  # URL pour le tableau de bord secrétariat
    elif user.role == 'etudiant':
        return redirect('etudiant_dashboard')  # URL pour le tableau de bord étudiant
    return redirect('upload_image')  # Redirection par défaut

@login_required
def update_user_password(request, username):
    """Vue pour mettre à jour le mot de passe d'un utilisateur (uniquement pour les admins)."""
    if not request.user.is_authenticated or request.user.role != 'admin':
        return redirect('login')  # Redirige si l'utilisateur n'est pas un admin
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        try:
            user = CustomUser.objects.get(username=username)
            user.password = make_password(new_password)
            user.save()
            return render(request, 'app/password_updated.html', {'message': f'Mot de passe mis à jour pour {username}'})
        except CustomUser.DoesNotExist:
            return render(request, 'app/password_updated.html', {'message': 'Utilisateur non trouvé'})
    return render(request, 'app/update_password.html', {'username': username})

# Autres vues existantes...
@login_required
def admin_dashboard(request):
    return render(request, 'app/admin_dashboard.html', {'user': request.user})

@login_required
def prof_dashboard(request):
    return render(request, 'app/prof_dashboard.html', {'user': request.user})

@login_required
def secretariat_dashboard(request):
    return render(request, 'app/secretariat_dashboard.html', {'user': request.user})

@login_required
def etudiant_dashboard(request):
    return render(request, 'app/etudiant_dashboard.html', {'user': request.user})