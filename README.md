Projet 110 – Groupe 14
    - Fortunat G2
    - Randy G1
    - Finoana G1
    - Finaritra G1

Étape 1:  créer environnement virtuel via commande :python -3.10 -m venv env 
          Puis pour l'activer il faut faire commande : .\env\Scripts\Activate.ps1

2/Dans le dossier du projet, créer un environnement virtuel Python 3.10 avec la commande appropriée (par exemple, sous Windows) :

    python3.10 -m venv env
puis activer le venv
    env\Scripts\activate  #windows
        ou
    source env/bin/activate #linux

3/Installer les dépendances nécessaires :
    pip install -r requirements.txt

4/Migration des bdd 
          --> py manage.py makemigrations
            puis
          --> py manage.py migrate

5/Creation superuser de django-admin
          --> py manage.py createsuperuser (suivre les concepts clé)
          --> py manage.py migrate

6/  **lorsque vous avez créer un utilisateur admin, prenez ou uplodez une image png ou jpeg dans image/ et renommer en Admin.jpg(écraser le fichier) puis lancer register_face.py pour enregistrer votre face comme facial de l'admin, ainsi vous pouvez vous connecter juste qu'on scannant grace à une reconnaissance faciale
                                ou sinon
    **vous pouver juste vous connecter en tant que admin sur "login" en insérarnt votre username et password. 
        **Avec username="aro321" et password="1234567890aro"**

6/Vérifier que votre connexion Internet fonctionne correctement.

7/Lancer le serveur Django avec :
    python manage.py runserver

**Pour plus de detail visualiser le fichier pdf concernant l'utilisation et l'importance de notre application local de gestion éléctronique des documents (GED)**

                                                         **Conclusion**
Au cours de la réalisation de notre projet GED, nous avons pris conscience de l’importance d’un système de Gestion Électronique des Documents, aussi bien dans un contexte professionnel que dans un cadre universitaire. Un tel outil facilite considérablement l’organisation, le stockage et l’accès aux documents, ce qui permet de gagner un temps précieux et d’améliorer l’efficacité globale des processus.

Par ailleurs, cette expérience nous a permis de renforcer notre capacité à travailler en équipe. Les activités de veille technologique et les échanges réguliers menés durant ces deux semaines ont favorisé une meilleure coordination, une répartition plus claire des tâches et un apprentissage collectif plus riche.                                                        