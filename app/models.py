from django.db import models
from django.contrib.auth.models import AbstractUser


# Pour organiser les niveaux d'étude
class Niveau(models.Model):
    nom = models.CharField(max_length=10)  # ex: L1, M1, etc.

    def __str__(self):
        return self.nom

# Pour organiser les filières (Informatique, Droit, etc.)
class Filiere(models.Model):
    nom = models.CharField(max_length=100)

    def __str__(self):
        return self.nom

# Étudiant lié à un niveau et une filière
class Etudiant(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    matricule = models.CharField(max_length=50, unique=True)
    niveau = models.ForeignKey(Niveau, on_delete=models.SET_NULL, null=True)
    filiere = models.ForeignKey(Filiere, on_delete=models.SET_NULL, null=True)
    photo = models.ImageField(upload_to="photos_etudiants/", blank=True, null=True)  # Pour reconnaissance faciale
    cv_text = models.TextField(blank=True)  # Pour lire avec ElevenLabs

    def __str__(self):
        return f"{self.nom} {self.prenom} ({self.matricule})"

# Documents liés à un étudiant
class Document(models.Model):
    TYPE_CHOICES = [
        ('releve', 'Relevé de notes'),
        ('certificat', 'Certificat de scolarité'),
        ('attestation', 'Attestation'),
        ('cv', 'CV'),
        ('autre', 'Autre'),
    ]

    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE)
    type_document = models.CharField(max_length=20, choices=TYPE_CHOICES)
    fichier = models.FileField(upload_to="documents/")
    date_ajout = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.etudiant} - {self.get_type_document_display()}"



class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('prof', 'Professeur'),
        ('secretariat', 'Secrétariat'),
        ('etudiant', 'Étudiant'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    photo = models.ImageField(upload_to="photos_utilisateurs/", blank=True, null=True)  # pour future reconnaissance faciale

    def __str__(self):
        return f"{self.username} ({self.role})"

