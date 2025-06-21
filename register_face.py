import os
import cv2
import mediapipe as mp
import pickle
import numpy as np
import django
from django.conf import settings

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GED.settings')
django.setup()

from django.contrib.auth import get_user_model
from app.models import UserProfile

User = get_user_model()

# Configuration de MediaPipe FaceMesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7,
    static_image_mode=True  # Optimisé pour les images statiques
)

def compute_landmark_distances(landmarks, img_shape=None):
    """Calcule les distances normalisées entre les points clés du visage"""
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

def update_existing_profiles():
    for profile in UserProfile.objects.all():
        user = profile.user
        image_path = f"images/{user.username}.jpg"
        register_face(user.username, image_path)

def register_face(username, image_path):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"L'utilisateur {username} n'existe pas. Veuillez d'abord créer l'utilisateur.")
        return

    img = cv2.imread(image_path)
    if img is None:
        print(f"Échec du chargement de l'image depuis {image_path}")
        return

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(img_rgb)
    
    if results.multi_face_landmarks:
        landmarks = results.multi_face_landmarks[0].landmark
        distances = compute_landmark_distances(landmarks, img.shape)
        
        if distances is not None:
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.face_landmarks = pickle.dumps(distances)
            profile.save()
            print(f"Visage enregistré pour {username}")
        else:
            print("Impossible de calculer les caractéristiques faciales")
    else:
        print("Aucun visage détecté dans l'image")

if __name__ == "__main__":
    # Exemple d'utilisation
    register_face("bebe", "image/Aro.jpg")