from django.contrib import admin
from .models import Document, CustomUser, Niveau, Filiere, Etudiant

admin.site.register(Document)
admin.site.register(CustomUser)
admin.site.register(Niveau)
admin.site.register(Filiere)
admin.site.register(Etudiant)
