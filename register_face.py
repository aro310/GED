# --- register_face.py ---
import os
import cv2
import face_recognition
import pickle
import numpy as np
import django
from django.conf import settings

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GED.settings')
django.setup()

from django.contrib.auth import get_user_model
from app.models import UserProfile, CustomUser

User = get_user_model()

def register_face(username, image_path=None):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"L'utilisateur {username} n'existe pas.")
        return

    # Utiliser l'image_path fourni
    if image_path:
        img = cv2.imread(image_path)
        if img is None:
            print(f"Erreur de chargement de {image_path}")
            return
    elif user.photo:
        img_path = os.path.join(settings.MEDIA_ROOT, user.photo.name)
        img = cv2.imread(img_path)
        if img is None:
            print(f"Erreur de chargement de la photo de {user.username} à {img_path}")
            return
    else:
        print(f"Aucune photo associée à {username}")
        return

    # Convertir l'image en RGB (face_recognition utilise RGB)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Détecter les visages et extraire les embeddings
    face_locations = face_recognition.face_locations(img_rgb)
    if not face_locations:
        print("Aucun visage détecté dans l'image.")
        return

    # Extraire l'embedding du premier visage détecté
    face_encoding = face_recognition.face_encodings(img_rgb, face_locations)[0]

    # Enregistrer l'embedding dans UserProfile
    profile, created = UserProfile.objects.get_or_create(user=user)
    profile.face_embedding = pickle.dumps(face_encoding)  # Sérialiser l'embedding
    profile.save()
    print(f"Embedding facial enregistré pour {username} à partir de {image_path or user.photo.name}")

if __name__ == "__main__":
    register_face("tsito", "image/Aro.jpeg")
    register_face("bebe", "image/Bebe.jpeg")
    register_face("hery", "image/Hery.jpeg")

    print("Enregistrement terminé. Vérifiez la base de données.")