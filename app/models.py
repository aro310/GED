from django.db import models
from django.contrib.auth.models import AbstractUser, User
from django.conf import settings



# =============================
# Utilisateur avec rôles
# =============================

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('prof', 'Professeur'),
        ('secretariat', 'Secrétariat'),
        ('etudiant', 'Étudiant'),
    ]

    role = models.CharField(max_length=20, choices=[('etudiant', 'Étudiant'), ('prof', 'Professeur')], default='etudiant')
    photo = models.ImageField(upload_to="photos_users/",blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    face_embedding = models.BinaryField(null=True, blank=True)  # Stocker l'embedding facial sérialisé

    def __str__(self):
        return f"Profil de {self.user.username}"

# =============================
# Niveau d'étude (L1, M1, etc.)
# =============================

class Niveau(models.Model):
    nom = models.CharField(max_length=10)  # Exemple : L1, M1, etc.

    def __str__(self):
        return self.nom


# =============================
# Filière (Informatique, Droit, etc.)
# =============================

class Filiere(models.Model):
    nom = models.CharField(max_length=100)

    def __str__(self):
        return self.nom


# =============================
# Étudiant
# =============================

class Etudiant(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    matricule = models.CharField(max_length=50, unique=True)
    niveau = models.ForeignKey(Niveau, on_delete=models.SET_NULL, null=True)
    filiere = models.ForeignKey(Filiere, on_delete=models.SET_NULL, null=True)
    photo = models.ImageField(upload_to="photos_etudiants/", blank=True, null=True)  # Pour reconnaissance faciale
    cv_text = models.TextField(blank=True)  # Pour lecture vocale avec ElevenLabs

    def __str__(self):
        return f"{self.nom} {self.prenom} ({self.matricule})"


# =============================
# Documents (CV, certificats, factures, paiements…)
# =============================

class Document(models.Model):
    TYPE_CHOICES = [
        ('releve', 'Relevé de notes'),
        ('certificat', 'Certificat de scolarité'),
        ('attestation', 'Attestation'),
        ('cv', 'CV'),
        ('paiement', 'Justificatif de paiement'),
        ('facture', 'Facture'),
        ('devoir', 'Devoir'),
        ('autre', 'Autre'),
    ]

    type_document = models.CharField(max_length=20, choices=TYPE_CHOICES)
    fichier = models.FileField(upload_to="documents/")
    date_ajout = models.DateTimeField(auto_now_add=True)

    # Lien facultatif vers un étudiant
    etudiant = models.ForeignKey(
        Etudiant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Laisser vide si le document ne concerne pas un étudiant"
    )

    # Qui a uploadé (admin, secrétaire…)
    uploaded_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Utilisateur ayant ajouté ce document"
    )

    def __str__(self):
        if self.etudiant:
            return f"{self.etudiant} - {self.get_type_document_display()}"
        return f"Document Général - {self.get_type_document_display()}"

class DocumentSharingRequest(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, null=True, blank=True)
    audio_path = models.CharField(max_length=500, blank=True, null=True, help_text="Chemin du fichier audio si applicable")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_requests')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_requests')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'En attente'), ('accepted', 'Accepté'), ('rejected', 'Rejeté')],
        default='pending'
    )

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username}: {self.document.fichier.name if self.document else 'Aucun document'}"
