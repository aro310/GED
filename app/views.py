import os
import cv2
import numpy as np
import mediapipe as mp
import pickle
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.conf import settings
from .forms import ImageUploadForm, CustomLoginForm, CustomUserCreationForm
from .models import Document, CustomUser, UserProfile
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

# GED/app/views.py (extrait)
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
    return render(request, 'app/upload.html', {'form': form, 'request': request})  # Passer 'request' au contexte

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

# Configuration de MediaPipe FaceMesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7,
    static_image_mode=False
)

def compute_landmark_distances(landmarks, img_shape=None):
    """Calcule les distances normalisées entre les points clés du visage."""
    if not landmarks:
        return None
        
    # Points clés (yeux, nez, bouche, contour visage)
    key_points = [33, 133, 362, 263, 1, 168, 199, 4, 5, 195, 197]
    distances = []
    
    # Conversion en coordonnées pixels si l'image est fournie
    if img_shape:
        h, w = img_shape[:2]
        landmarks = [(lm.x * w, lm.y * h) for lm in landmarks]
    
    # Calcul des distances euclidiennes
    for i in range(len(key_points)):
        for j in range(i + 1, len(key_points)):
            p1 = landmarks[key_points[i]]
            p2 = landmarks[key_points[j]]
            
            if img_shape:
                dist = np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
            else:
                dist = np.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)
            
            distances.append(dist)
    
    # Normalisation par la distance inter-oculaire
    if img_shape:
        left_eye = landmarks[33]
        right_eye = landmarks[263]
        norm_factor = np.sqrt((left_eye[0] - right_eye[0])**2 + (left_eye[1] - right_eye[1])**2)
    else:
        norm_factor = np.sqrt((landmarks[33].x - landmarks[263].x)**2 + 
                              (landmarks[33].y - landmarks[263].y)**2)
    
    return np.array(distances) / (norm_factor + 1e-8)  # Évite la division par zéro

def face_view(request):
    if request.method == 'POST':
        image_data = request.FILES.get('image')
        if not image_data:
            messages.error(request, "Aucune image téléversée.")
            return redirect('face')
        
        # Validation de la taille et du format de l'image
        max_size = 10 * 1024 * 1024  # 10 Mo
        if image_data.size > max_size:
            messages.error(request, "L'image dépasse la taille maximale de 10 Mo.")
            return redirect('face')
        
        allowed_types = ['image/jpeg', 'image/png', 'image/gif']
        if image_data.content_type not in allowed_types:
            messages.error(request, "Format d'image non pris en charge. Utilisez JPEG, PNG ou GIF.")
            return redirect('face')
        
        print("Tentative de connexion reçue")
        try:
            # Conversion et prétraitement de l'image
            nparr = np.frombuffer(image_data.read(), np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Échec du décodage de l'image.")
            
            img = cv2.flip(img, 1)  # Miroir pour un effet naturel
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Détection des landmarks
            results = face_mesh.process(img_rgb)
            
            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark
                current_distances = compute_landmark_distances(landmarks, img.shape)
                
                if current_distances is not None:
                    print("Distances des landmarks:", current_distances)
                    
                    best_match = None
                    best_ratio = 0
                    
                    for profile in UserProfile.objects.all():
                        if not profile.face_landmarks:
                            continue
                            
                        stored_distances = pickle.loads(profile.face_landmarks)
                        min_length = min(len(stored_distances), len(current_distances))
                        diff = np.abs(stored_distances[:min_length] - current_distances[:min_length])
                        passed_ratio = np.sum(diff < 0.06) / min_length  # Ratio de correspondance
                        
                        print(f"Comparaison avec {profile.user.username} - Ratio: {passed_ratio:.2f}")
                        
                        if passed_ratio > best_ratio:
                            best_ratio = passed_ratio
                            best_match = profile.user
                    
                    if best_ratio > 0.95:  # Seuil de correspondance
                        login(request, best_match)
                        messages.success(request, f"Connexion réussie pour {best_match.username} !")
                        print(f"Connexion réussie pour {best_match.username}")
                        return redirect('upload_images')
                    else:
                        messages.error(request, "Aucun profil ne correspond avec une précision suffisante.")
                else:
                    messages.error(request, "Impossible de calculer les caractéristiques faciales.")
            else:
                messages.error(request, "Aucun visage détecté dans l'image.")
                
        except Exception as e:
            messages.error(request, f"Erreur lors du traitement: {str(e)}")
            print("Erreur détaillée:", repr(e))
        
        return redirect('face')
    
    return render(request, 'app/face.html')

def home_view(request):
    if not request.user.is_authenticated:
        return redirect('face')
    return render(request, 'app/upload.html', {'user': request.user})  # Passer l'utilisateur au contexte


def liste_fichiers(request):
    dossier = os.path.join(settings.MEDIA_ROOT, 'documents')

    fichiers = []
    fichiers_urls = []

    if os.path.exists(dossier):
        fichiers = sorted(os.listdir(dossier), key=lambda x: x.lower()) #non sensible a la casse  # Trie alphabétique croissant
        fichiers_urls = [{'nom': f, 'url': os.path.join('documents', f)} for f in fichiers]

    return render(request, 'app/liste_fichiers.html', {
        'fichiers': fichiers_urls,
        'media_url': settings.MEDIA_URL,
    })

