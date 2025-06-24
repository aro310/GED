# --- register_face.py ---
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
from app.models import UserProfile, CustomUser

User = get_user_model()

# Configuration de MediaPipe FaceMesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7,
    static_image_mode=True
)

def compute_landmark_distances(landmarks, img_shape=None):
    if not landmarks:
        return None

    key_points = [33, 133, 362, 263, 1, 168, 199, 4, 5, 195, 197]
    distances = []

    if img_shape:
        h, w = img_shape[:2]
        landmarks = [(lm.x * w, lm.y * h) for lm in landmarks]

    for i in range(len(key_points)):
        for j in range(i + 1, len(key_points)):
            p1 = landmarks[key_points[i]]
            p2 = landmarks[key_points[j]]

            if img_shape:
                dist = np.linalg.norm(np.array(p1) - np.array(p2))
            else:
                dist = np.linalg.norm(np.array([p1.x, p1.y]) - np.array([p2.x, p2.y]))

            distances.append(dist)

    if img_shape:
        left_eye = landmarks[33]
        right_eye = landmarks[263]
        norm_factor = np.linalg.norm(np.array(left_eye) - np.array(right_eye))
    else:
        norm_factor = np.linalg.norm(np.array([landmarks[33].x, landmarks[33].y]) -
                                     np.array([landmarks[263].x, landmarks[263].y]))

    return np.array(distances) / (norm_factor + 1e-8)


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
    else:
        print(f"Aucun image_path fourni, veuillez spécifier une image.")
        return

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(img_rgb)

    if results.multi_face_landmarks:
        landmarks = results.multi_face_landmarks[0].landmark
        distances = compute_landmark_distances(landmarks, img.shape)
        if distances is not None:
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.face_landmarks = pickle.dumps(distances)  # Remplacer l'ancien ensemble
            profile.save()
            print(f"Landmarks enregistrés pour {username} à partir de {image_path}")
        else:
            print("Erreur calcul distances")
    else:
        print("Aucun visage détecté")

if __name__ == "__main__":
    print("Enregistrement pour tsito avec Aro.jpeg")
    register_face("tsito", "image/Aro.jpeg")
    print("Enregistrement pour bebe avec Bebe.jpeg")
    register_face("bebe", "image/Bebe.jpeg")
    print("Enregistrement terminé. Vérifiez la base de données.")