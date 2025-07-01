import os
from os import walk, path
import cv2
import numpy as np
import face_recognition
import mediapipe as mp
import pickle
from django.http import HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.conf import settings
from .forms import ImageUploadForm, CustomLoginForm, CustomUserCreationForm,UserUpdateForm
from .models import Document, CustomUser, UserProfile,DocumentSharingRequest, User
from .ocr_utils import extraire_texte_depuis_image
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from io import BytesIO
import pytesseract
import traceback
from elevenlabs.client import ElevenLabs
from collections import defaultdict

# Configurer Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tessdata_dir_config = r'--tessdata-dir "C:\Program Files\Tesseract-OCR\tessdata"'

# Initialiser le client ElevenLabs
client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)

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

# GED/app/views.py (extrait)
from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .forms import ImageUploadForm
from .models import Document
from PIL import Image
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os
import traceback

@login_required
def upload_image(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            image = form.cleaned_data['image']
            type_folder = form.cleaned_data.get('type_document', 'autre')
            convertir_pdf = form.cleaned_data.get('convertir_en_pdf', True)

            # Chemin de base
            user_folder = os.path.join(settings.MEDIA_ROOT, 'documents', request.user.username, type_folder)
            os.makedirs(user_folder, exist_ok=True)

            # Enregistrement temporaire de l’image
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            image_path = os.path.join(temp_dir, image.name)
            with open(image_path, 'wb+') as f:
                for chunk in image.chunks():
                    f.write(chunk)

            try:
                with Image.open(image_path) as img:
                    texte = extraire_texte_depuis_image(image_path)

                is_error = texte.startswith("Erreur") if texte else False
                if is_error or not texte:
                    raise Exception(texte or "Aucun texte extrait.")

                # --- Création du fichier PDF si demandé ---
                if convertir_pdf:
                    pdf_buffer = BytesIO()
                    pdf = canvas.Canvas(pdf_buffer, pagesize=A4)
                    pdf.setFont("Helvetica", 12)
                    text_object = pdf.beginText(40, A4[1] - 40)
                    for line in texte.split('\n'):
                        text_object.textLine(line)
                    pdf.drawText(text_object)
                    pdf.save()

                    pdf_name = image.name.rsplit('.', 1)[0] + '.pdf'
                    pdf_path = os.path.join(user_folder, pdf_name)

                    with open(pdf_path, 'wb') as f:
                        f.write(pdf_buffer.getvalue())
                    fichier_final = os.path.join('documents', request.user.username, type_folder, pdf_name)

                    pdf_buffer.close()
                else:
                    # Si on ne convertit pas en PDF, on garde l'image originale
                    final_image_path = os.path.join(user_folder, image.name)
                    with open(final_image_path, 'wb+') as f:
                        f.write(open(image_path, 'rb').read())
                    fichier_final = os.path.join('documents', request.user.username, type_folder, image.name)

                # --- Génération Audio ---
                audio_name = image.name.rsplit('.', 1)[0] + '.mp3'
                audio_path = os.path.join(settings.MEDIA_ROOT, 'audio', request.user.username, audio_name)
                os.makedirs(os.path.dirname(audio_path), exist_ok=True)

                audio = client.text_to_speech.convert(
                    text=texte,
                    voice_id="SOYHLrjzK2X1ezoPC6cr",
                    model_id="eleven_multilingual_v2",
                    output_format="mp3_44100_128",
                )
                with open(audio_path, 'wb') as f:
                    for chunk in audio:
                        f.write(chunk)

                # --- Enregistrement en base de données ---
                document = Document(
                    type_document=type_folder,
                    fichier=fichier_final,
                    uploaded_by=request.user
                )
                # Ajout de l'étudiant si c’est un personnel (champ présent dans le formulaire)
                if 'etudiant' in form.cleaned_data and form.cleaned_data['etudiant']:
                    document.etudiant = form.cleaned_data['etudiant']
                document.save()

                # Nettoyage du fichier temporaire
                if os.path.exists(image_path):
                    os.remove(image_path)

                # Préparation des fichiers de l’utilisateur
                user_files_urls = []
                user_root = os.path.join(settings.MEDIA_ROOT, 'documents', request.user.username)
                if os.path.exists(user_root):
                    for root, dirs, files in os.walk(user_root):
                        for file in files:
                            rel_path = os.path.relpath(os.path.join(root, file), user_root)
                            user_files_urls.append({
                                'nom': rel_path,
                                'url': os.path.join(settings.MEDIA_URL, 'documents', request.user.username, rel_path)
                            })

                return render(request, 'app/resultat.html', {
                    'document': document,
                    'texte': texte,
                    'audio_url': os.path.join(settings.MEDIA_URL, 'audio', request.user.username, audio_name),
                    'user_files': sorted(user_files_urls, key=lambda x: x['nom'].lower()),
                    'is_error': False
                })

            except Exception as e:
                if os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except PermissionError:
                        pass
                print(traceback.format_exc())
                return render(request, 'app/resultat.html', {'texte': str(e), 'is_error': True})
    else:
        form = ImageUploadForm(user=request.user)

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
        form = CustomUserCreationForm(request.POST, request.FILES)  # Inclure request.FILES
        if  form.is_valid():
            form.save()
        else:
            print("Erreurs du formulaire:", form.errors)  # Débogage des erreurs
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
import os
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render
from django.contrib.auth import get_user_model

@login_required
def admin_dashboard(request):
    if request.user.role != 'admin':
        return HttpResponseForbidden("Accès réservé à l'administrateur.")

    # --- 1. Charger les utilisateurs ---
    CustomUser = get_user_model()
    users = CustomUser.objects.exclude(id=request.user.id)  # ne pas afficher l'admin lui-même

    # --- 2. Gérer l’exploration de /media/documents/ ---
    base_path = os.path.join(settings.MEDIA_ROOT, 'documents')
    os.makedirs(base_path, exist_ok=True)

    current_path = request.GET.get('path', '')
    abs_path = os.path.abspath(os.path.join(base_path, current_path))

    # Sécurité : empêcher l'accès hors dossier autorisé
    if not abs_path.startswith(base_path):
        return HttpResponseForbidden("Chemin non autorisé.")

    folders = []
    files = []

    try:
        for name in os.listdir(abs_path):
            full_path = os.path.join(abs_path, name)
            rel_path = os.path.relpath(full_path, base_path).replace("\\", "/")
            if os.path.isdir(full_path):
                folders.append({'name': name, 'path': rel_path})
            elif os.path.isfile(full_path):
                files.append({'name': name, 'path': rel_path})
    except Exception as e:
        print("Erreur lecture documents :", e)

    # --- 3. Gestion AJAX ---
    if request.GET.get('ajax') == '1' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
        data = {
            'folders': folders,
            'files': files,
            'current_path': current_path,
        }
        return JsonResponse(data)

    # --- 4. Rendre la page complète ---
    return render(request, 'app/admin_dashboard.html', {
        'user': request.user,
        'users': users,
        'folders': folders,
        'files': files,
        'current_path': current_path,
        'MEDIA_URL': settings.MEDIA_URL,
    })



@login_required
def profs_dashboard(request):
    if request.user.role != 'prof':
        return HttpResponseForbidden("Accès refusé : seuls les professeurs peuvent accéder à cette page.")

    sharing_requests = DocumentSharingRequest.objects.select_related('document').filter(receiver=request.user).order_by('-created_at')

    accepted_files = [
        {
            'url': req.document.fichier.url,
            'name': os.path.basename(req.document.fichier.name)
        }
        for req in sharing_requests if req.status == 'accepted' and req.document and req.document.fichier
    ]

    accepted_audio = [
    {
        'url': os.path.join(settings.MEDIA_URL, req.audio_path).replace('\\', '/'),
        'name': os.path.basename(req.audio_path)
    }
    for req in sharing_requests if req.status == 'accepted' and req.audio_path
    ]

    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        if 'accept_request' in request.POST:
            try:
                request_obj = DocumentSharingRequest.objects.get(id=request_id, receiver=request.user)
                request_obj.status = 'accepted'
                request_obj.save()
            except DocumentSharingRequest.DoesNotExist:
                print("Demande non trouvée")
        elif 'reject_request' in request.POST:
            try:
                request_obj = DocumentSharingRequest.objects.get(id=request_id, receiver=request.user)
                request_obj.status = 'rejected'
                request_obj.save()
            except DocumentSharingRequest.DoesNotExist:
                print("Demande non trouvée")

    return render(request, 'app/prof_dashboard.html', {
        'user': request.user,
        'request': request,
        'sharing_requests': sharing_requests,
        'accepted_files': accepted_files,
        'accepted_audio': accepted_audio,
        'media_url': settings.MEDIA_URL,
    })

@login_required
def etudiant_dashboard(request):
    user = request.user
    query = request.GET.get('q', '').strip()

    grouped_files = defaultdict(list)
    grouped_audio_files = defaultdict(list)
    audio_extensions = ('.mp3', '.wav', '.ogg')

    # ---------------------
    # 1. Documents (PDF, images, audio dans /documents/)
    user_doc_path = path.join(settings.MEDIA_ROOT, 'documents', user.username)
    if path.exists(user_doc_path):
        try:
            for root, dirs, files in walk(user_doc_path):
                for file in files:
                    full_path = path.join(root, file)
                    if not path.isfile(full_path):
                        continue

                    rel_path = path.relpath(full_path, user_doc_path)
                    parts = rel_path.split(path.sep)
                    folder = parts[0] if len(parts) > 1 else "Autres"
                    file_url = path.join(settings.MEDIA_URL, 'documents', user.username, *parts).replace('\\', '/')

                    if not query or query.lower() in rel_path.lower():
                        # Catégorie : PDF/images
                        if file.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png', '.gif')):
                            grouped_files[folder].append({
                                'nom': file,
                                'url': file_url,
                                'rel_path': rel_path
                            })
                        # Catégorie : audio dans documents/
                        elif file.lower().endswith(audio_extensions):
                            grouped_audio_files[folder].append({
                                'nom': file,
                                'url': file_url,
                                'rel_path': rel_path
                            })
        except Exception as e:
            print(f"Erreur lors de l'exploration de /documents : {e}")

    # ---------------------
    # 2. Fichiers audio dans /audio/<username>/
    audio_dir = os.path.join(settings.MEDIA_ROOT, 'audio', user.username)
    if os.path.exists(audio_dir):
        try:
            for root, _, files in os.walk(audio_dir):
                folder = os.path.relpath(root, audio_dir)
                folder = folder if folder != '.' else 'Racine'
                for f in files:
                    if f.lower().endswith(audio_extensions):
                        abs_path = os.path.join(root, f)
                        rel_path = os.path.relpath(abs_path, settings.MEDIA_ROOT)
                        grouped_audio_files[folder].append({
                            'nom': f,
                            'url': os.path.join(settings.MEDIA_URL, rel_path).replace('\\', '/'),
                            'rel_path': os.path.relpath(abs_path, path.join(settings.MEDIA_ROOT, 'audio', user.username))
                        })
        except Exception as e:
            print(f"Erreur lors de l'exploration de /audio : {e}")

    # ---------------------
    # 3. Partage de document
    if request.method == 'POST' and 'share_document' in request.POST:
        document_path = request.POST.get('document_path')
        receiver_id = request.POST.get('receiver')

        if document_path and receiver_id:
            try:
                receiver = get_user_model().objects.get(id=receiver_id)
                document_relative_path = path.join('documents', user.username, document_path)
                document = Document.objects.filter(fichier=document_relative_path).first()

                if document:
                    DocumentSharingRequest.objects.create(
                        document=document,
                        sender=user,
                        receiver=receiver
                    )
                else:
                    print(f"Document introuvable : {document_relative_path}")
            except get_user_model().DoesNotExist:
                print("Utilisateur destinataire non trouvé")
    elif 'share_audio' in request.POST:
        audio_path = request.POST.get('audio_path')
        receiver_id = request.POST.get('receiver')
        if audio_path and receiver_id:
            try:
                receiver = get_user_model().objects.get(id=receiver_id)
                DocumentSharingRequest.objects.create(
                    audio_path=os.path.join('audio', user.username, audio_path),
                    sender=user,
                    receiver=receiver
                )
            except get_user_model().DoesNotExist:
                print("Professeur non trouvé pour partage audio")

    # ---------------------
    # 4. Préparer le contexte
    professors = get_user_model().objects.filter(role='prof')

    return render(request, 'app/etudiant_dashboard.html', {
        'user': user,
        'request': request,
        'form': ImageUploadForm(),
        'grouped_files': dict(grouped_files),
        'grouped_audio_files': dict(grouped_audio_files),
        'media_url': settings.MEDIA_URL,
        'query': query,
        'all_files': ["/".join([key, f['nom']]) for key in grouped_files for f in grouped_files[key]],
        'professors': professors
    })

@login_required
def secretariat_dashboard(request):
    return render(request, 'app/secretariat_dashboard.html', {'user': request.user})

from collections import defaultdict


@csrf_exempt
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
            
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Détecter les visages et extraire l'embedding
            face_locations = face_recognition.face_locations(img_rgb)
            if not face_locations:
                messages.error(request, "Aucun visage détecté dans l'image.")
                return redirect('face')
            
            current_encoding = face_recognition.face_encodings(img_rgb, face_locations)[0]
            
            best_match = None
            best_distance = float('inf')
            
            for profile in UserProfile.objects.all():
                if not profile.face_embedding:
                    continue
                
                stored_encoding = pickle.loads(profile.face_embedding)
                # Calculer la distance entre les embeddings
                distance = np.linalg.norm(np.array(stored_encoding) - np.array(current_encoding))
                print(f"Comparaison avec {profile.user.username} - Distance: {distance:.2f}")
                
                # Mettre à jour le meilleur match uniquement si la distance est inférieure au seuil
                if distance < best_distance and distance < 0.6:
                    best_distance = distance
                    best_match = profile.user
            
            print(f"Meilleur match: {best_match.username if best_match else 'Aucun'} avec distance: {best_distance:.2f}")
            if best_match and best_distance < 0.5:
                login(request, best_match)
                messages.success(request, f"Connexion réussie pour {best_match.username} !")
                print(f"Connexion réussie pour {best_match.username}")
                return redirect_by_role(best_match)
            else:
                messages.error(request, "Aucune correspondance valide trouvée.")
                return redirect('face')  # Redirection par défaut si pas de match
            
        except Exception as e:
            messages.error(request, f"Erreur lors du traitement: {str(e)}")
            print("Erreur détaillée:", repr(e))
        
        return redirect('face')
    
    return render(request, 'app/face.html')

def redirect_by_role(user):
    """Redirige l'utilisateur selon son rôle."""
    if hasattr(user, 'role'):  # Vérifie si l'attribut role existe
        if user.role == 'admin':
            return redirect('admin_dashboard')
        elif user.role == 'prof':
            return redirect('prof_dashboard')
        elif user.role == 'secretariat':
            return redirect('secretariat_dashboard')
        elif user.role == 'etudiant':
            return redirect('etudiant_dashboard')
    return redirect('upload_image')  # Redirection par défaut si aucun rôle ou rôle inconnu

def home_view(request):
    if not request.user.is_authenticated:
        return redirect('face')
    return render(request, 'app/upload.html', {'user': request.user})  # Passer l'utilisateur au contexte


from django.shortcuts import redirect

@login_required
def delete_user(request, user_id):
    if request.user.role != 'admin':
        return HttpResponseForbidden("Accès refusé.")

    CustomUser = get_user_model()
    try:
        user = CustomUser.objects.get(id=user_id)
        if user != request.user:  # sécurité : ne pas supprimer soi-même
            user.delete()
    except CustomUser.DoesNotExist:
        pass

    return redirect('admin_dashboard')

@login_required
def edit_user(request, user_id):
    if request.user.role != 'admin':
        return HttpResponseForbidden("Accès interdit.")

    CustomUser = get_user_model()
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('admin_dashboard')
    else:
        form = UserUpdateForm(instance=user)

    return render(request, 'app/edit_user.html', {
        'form': form,
        'user_to_edit': user
    })

@require_POST
@login_required
def delete_entry(request):
    if request.user.role != 'admin':
        return HttpResponseForbidden("Accès refusé.")

    rel_path = request.POST.get('path')
    target_path = os.path.join(settings.MEDIA_ROOT, 'documents', rel_path)

    if os.path.exists(target_path):
        if os.path.isfile(target_path):
            os.remove(target_path)
        elif os.path.isdir(target_path):
            import shutil
            shutil.rmtree(target_path)
        messages.success(request, "Élément supprimé.")
    else:
        messages.error(request, "Fichier ou dossier introuvable.")

    return redirect('admin_dashboard')



from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import Document, Niveau, Filiere, Etudiant, DocumentSharingRequest
import logging

# Configurer le logging
logger = logging.getLogger(__name__)

from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import Document, DocumentSharingRequest
from .gemini_api import chat_with_gemini
from .keywords import recent_doc_keywords, sharing_keywords, regulation_keywords, greeting_keywords, presentation_keywords, user_list_keywords, features_keywords, admin_keywords, normalize_text  # Importation des mots-clésimport logging
import os
from collections import defaultdict
import unicodedata

# Configurer le logging
logger = logging.getLogger(__name__)

@login_required
def gemini_chat(request):
    response_text = None
    user = request.user

    # Vérifier si c'est la première interaction
    if 'first_interaction' not in request.session:
        request.session['first_interaction'] = True
    is_first_interaction = request.session.get('first_interaction', False)

    if request.method == "POST":
        user_input = request.POST.get("message", "").lower().strip()  # Déjà en minuscules
        normalized_input = normalize_text(user_input)  # Normalisation supplémentaire
        logger.info(f"Utilisateur {user.username} (rôle: {user.role}) a envoyé : {user_input} (normalisé: {normalized_input})")

        # Mettre à jour le statut après la première interaction
        if is_first_interaction:
            request.session['first_interaction'] = False

        # Préparer le contexte de base pour l'IA
        if is_first_interaction:
            context = f"Tu es GEDbot, un assistant IA amical et utile de l'application GED de l'ESTI. C'est la première interaction avec {user.username} ({user.role}). Accueille-le chaleureusement avec 'Salut' ou 'Bonjour' et réponds en français, de manière engageante. Si la question est hors sujet, invite à poser une question pertinente (ex. 'documents récents', 'partager', 'règles LMD'). Question : {user_input}"
        else:
            context = f"Tu es GEDbot, un assistant IA utile de l'application GED de l'ESTI. Réponds à {user.username} ({user.role}) en français, de manière engageante, sans salutation répétitive. Si la question est hors sujet, invite à poser une question pertinente (ex. 'documents récents', 'partager', 'règles LMD'). Question : {user_input}"

        # Enrichir le contexte selon l'intention détectée
        if any(keyword in normalized_input for keyword in greeting_keywords):
            context += "\nContexte : L'utilisateur te salue. Réponds avec un accueil chaleureux."

        elif any(keyword in normalized_input for keyword in presentation_keywords):
            if is_first_interaction:
                context += "\nContexte : L'utilisateur te demande de te présenter lors de la première interaction. Décris ton rôle à l'ESTI avec un 'Salut'."
            else:
                context += "\nContexte : L'utilisateur te demande de te présenter. Décris ton rôle à l'ESTI sans salutation."

        elif any(keyword in normalized_input for keyword in user_list_keywords):
            CustomUser = get_user_model()
            users = CustomUser.objects.all()
            if users.exists():
                user_list = "\n".join(f"- {u.username} ({u.role})" for u in users)
                context += f"\nDonnées : Liste des utilisateurs enregistrés à l'ESTI :\n{user_list}"
            else:
                context += "\nDonnées : Aucun utilisateur enregistré pour l’instant."

        elif any(keyword in normalized_input for keyword in recent_doc_keywords):
            docs = Document.objects.filter(uploaded_by=user).order_by("-date_ajout")[:5]
            if docs.exists():
                doc_list = "\n".join(
                    f"- {os.path.basename(d.fichier.name)} ({d.date_ajout.strftime('%d/%m/%Y')}) [{d.get_type_document_display()}]"
                    for d in docs
                )
                context += f"\nDonnées : Les documents récents de {user.username} sont :\n{doc_list}"
            else:
                context += f"\nDonnées : {user.username} n'a pas encore de documents récents."

        elif any(keyword in normalized_input for keyword in sharing_keywords):
            requests = DocumentSharingRequest.objects.filter(sender=user).order_by("-created_at")
            if requests.exists():
                req_list = "\n".join(
                    f"- {req.receiver.username} ({req.status}) [{os.path.basename(req.document.fichier.name) if req.document else req.audio_path}]"
                    for req in requests if req.document or req.audio_path
                )
                context += f"\nDonnées : Les demandes de partage de {user.username} sont :\n{req_list}"
            else:
                context += f"\nDonnées : {user.username} n'a pas encore de demandes de partage."

        elif any(keyword in normalized_input for keyword in regulation_keywords):
            context += (
                "\nDonnées : Règles LMD à l’ESTI 2024-2025 :\n"
                "✔️ Admis : Toutes les UE validées.\n"
                "🟡 Admissible : Passage avec UE à rattraper.\n"
                "🔁 Redoublement : Moyenne ≤ 10/20.\n"
                "📌 UE validée si moyenne ≥ 10/20 (coefficient = crédits).\n"
                "⚠️ Note < 5/20 annule la validation.\n"
                "📈 Passage L2/L3 : Moyenne ≥ 10/20.\n"
                "🎓 Parcours L2 : Réseaux/Systèmes ou Intégration/Développement."
            )

        elif any(keyword in normalized_input for keyword in features_keywords):
            context += "\nContexte : L'utilisateur te demande tes fonctionnalités. Réponds avec : Je propose la reconnaissance faciale, réservée à l'admin qui est M. Finoana, la transformation d'images en PDF et audio par les élèves, qui peuvent ensuite être partagés avec les professeurs au choix, et les profs peuvent accepter ou refuser. Ajoute une invitation à demander de l'aide si pertinent."

        elif any(keyword in normalized_input for keyword in admin_keywords):
            context += "\nContexte : L'utilisateur te demande qui est l'admin. Réponds avec : L'admin est M. Finoana."

        # Appel à l'IA pour générer la réponse (toujours exécuté)
        response_text = chat_with_gemini(context)
        logger.info(f"Réponse générée par chat_with_gemini : {response_text}")

        # Vérification et secours si la réponse IA est vide ou hors sujet
        if not response_text or any(phrase in response_text.lower() for phrase in ["je ne sais pas", "hors sujet", "erreur"]):
            # Simulation de NLP : analyser le sentiment et proposer une réponse
            positive_words = ["merci", "super", "bien", "cool"]
            negative_words = ["problème", "erreur", "aide", "bug"]
            sentiment = "neutre"
            if any(word in normalized_input for word in positive_words):
                sentiment = "positif"
            elif any(word in normalized_input for word in negative_words):
                sentiment = "négatif"

            if sentiment == "positif":
                response_text = (
                    f"Content que tu sois de bonne humeur, {user.username} ! 😄 Je n’ai pas compris '{user_input}', "
                    "mais dis-m’en plus sur tes docs ou tes profs !"
                )
            elif sentiment == "négatif":
                response_text = (
                    f"Oups, {user.username}, un souci avec '{user_input}' ? Je suis là pour aider ! "
                    "Parle-moi de tes documents ou d’un problème."
                )
            else:
                response_text = (
                    f"Hmm, {user.username}, '{user_input}' me laisse perplexe. Je suis GEDbot, ton IA à l’ESTI ! "
                    "Essaie 'documents récents', 'partager', ou les 'règles LMD' !"
                )
            logger.warning(f"Réponse IA invalide, secours activé (sentiment: {sentiment})")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'response': response_text})

    return render(request, "app/gemini_chat.html", {"response": response_text})