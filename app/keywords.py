# Fonction pour normaliser le texte (insensible à la casse et aux accents)
def normalize_text(text):
    if not isinstance(text, str):
        return ""
    # Convertir en minuscules et normaliser les accents
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII').lower()
    return text

import unicodedata

# Listes de mots-clés enrichies
recent_doc_keywords = [
    "documents recents",
    "derniers fichiers",
    "mes derniers docs",
    "fichiers recents",
    "recent documents",
    "last files",
    "nouveaux documents",
    "documents nouveaux",
    "dernieres archives",
    "mes archives recentes",
    "fichiers derniers",
    "dernier document",
    "nouveaux fichiers",
    "files recents",
    "recent papers",
    "latest docs",
    "my recent files",
    "new documents",
    "recent uploads",
    "last uploads"
]

sharing_keywords = [
    "partager",
    "partagés",
    "demande de partage",
    "partage de fichier",
    "envoyer doc",
    "share document",
    "partage fichier",
    "envoyer document",
    "partage dossier",
    "demande envoi",
    "transfert fichier",
    "share file",
    "send document",
    "file sharing",
    "document transfer",
    "envoyer a prof",
    "partage avec prof",
    "demande partage prof",
    "transmettre fichier"
]

regulation_keywords = [
    "reglement",
    "regles",
    "lmd",
    "systeme lmd",
    "conditions",
    "regulations",
    "regle lmd",
    "regles universitaires",
    "normes lmd",
    "conditions etudes",
    "reglement etudes",
    "systeme educatif",
    "regles scolaires",
    "lmd rules",
    "education regulations",
    "study conditions",
    "academic rules",
    "university norms",
    "lmd system rules"
]

greeting_keywords = [
    "bonjour",
    "salut",
    "hello",
    "coucou",
    "bonsoir",
    "salutations",
    "hey",
    "hi there",
    "good morning",
    "good evening",
    "bienvenue",
    "salut a toi",
    "bon matin",
    "hello friend",
    "greetings"
]

presentation_keywords = [
    "que faites vous",
    "qui êtes vous",
    "présentez vous",
    "votre rôle",
    "c quoi ton job",
    "qui es tu",
    "que fais tu",
    "ton role",
    "presentation",
    "qui es-tu",
    "quel est ton travail",
    "a quoi sers tu",
    "decris toi",
    "what do you do",
    "your role",
    "introduce yourself",
    "qui es tu gedbot",
    "parle de toi",
    "qui tu es",
    "raconte moi"
]

user_list_keywords = [
    "liste des utilisateurs",
    "qui utilise",
    "utilisateurs inscrits",
    "membres",
    "liste users",
    "liste des membres",
    "utilisateurs actifs",
    "qui est inscrit",
    "membres inscrits",
    "user list",
    "active users",
    "registered members",
    "who is using",
    "list of users"
]

features_keywords = [
    "quels sont vos fonctionnalitéeeees",
    "fonctionnalités",
    "que pouvez vous faire",
    "vos capacités",
    "quelles sont vos fonctions",
    "vos competences",
    "que sais tu faire",
    "capacites gedbot",
    "fonctions disponibles",
    "what can you do",
    "your features",
    "capabilities",
    "what are your skills",#
    "available functions",
    "OCR",
]

admin_keywords = [
    "qui est l'admin",
    "admin",
    "administrateur",
    "qui gere",
    "qui est responsable",
    "admin principal",
    "gestionnaire",
    "chef admin",
    "who is the admin",
    "administrator",
    "who manages",
    "main admin"
]

# Nouveaux mots-clés pour les remarques
remark_keywords = [
    "remarques",
    "remarque",
    "commentaires",
    "profs",
    "professeur",
    "commentaires profs",
    "remarques professeurs",
    "avis profs",
    "notes profs",
    "feedback profs",
    "commentaires enseignants",
    "remarques enseignants"
]

# Nouveaux mots-clés pour introduire une fonction
function_intro_keywords = [
    "introduire fonction",
    "nouvelle fonction",
    "ajouter fonction",
    "nouveau feature",
    "introduire feature",
    "nouvelle capacité",
    "ajouter capacité",
    "new function",
    "introduce function",
    "add feature",
    "new capability"
]