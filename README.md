# GED

Étape 1:  créer environnement virtuel via commande :python -3.10 -m venv env 
          Puis pour l'activer il faut faire commande : .\env\Scripts\Activate.ps1

Étape 2:  Installation des librairies python qui sont dans requirements.txt 
          --> pip install -r requirements.txt

Étape 3:  Migration des bdd 
          --> py manage.py makemigrations
          --> py manage.py migrate

Étape 4:  Creation superuser de django-admin
          -->py manage.py createsuperuser (suivre les concepts clé)


Étape 5:  Lancer projet
          -->py manage.py runserver
