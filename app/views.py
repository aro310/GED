import os
from django.shortcuts import render
from django.conf import settings
from .forms import ImageUploadForm
from .models import Document
from .ocr_utils import extraire_texte_depuis_image
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from io import BytesIO
import pytesseract
import traceback
from elevenlabs.client import ElevenLabs

# Configurer Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tessdata_dir_config = r'--tessdata-dir "C:\Program Files\Tesseract-OCR\tessdata"'

# Initialiser le client ElevenLabs
client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)

def upload_image(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            print("Données du formulaire :", form.cleaned_data)  # Débogage
            image = form.cleaned_data['image']
            image_path = os.path.join(settings.MEDIA_ROOT, 'temp', image.name)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)

            # Enregistrer l'image temporairement
            with open(image_path, 'wb+') as f:
                for chunk in image.chunks():
                    f.write(chunk)

            try:
                # Extraire le texte avec Tesseract
                with Image.open(image_path) as img:
                    texte = extraire_texte_depuis_image(image_path)

                # Vérifier si du texte a été extrait
                if not texte or texte.startswith("Erreur OCR"):
                    raise Exception("Aucun texte extrait ou erreur OCR")

                # Créer un PDF avec le texte extrait
                pdf_buffer = BytesIO()
                pdf = canvas.Canvas(pdf_buffer, pagesize=A4)
                pdf.setFont("Helvetica", 12)
                text_object = pdf.beginText(40, A4[1] - 40)  # Marge de 40 points
                for line in texte.split('\n'):
                    text_object.textLine(line)
                pdf.drawText(text_object)
                pdf.save()

                # Nom du fichier PDF
                pdf_name = image.name.rsplit('.', 1)[0] + '.pdf'
                pdf_path = os.path.join(settings.MEDIA_ROOT, 'documents', pdf_name)
                os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

                # Enregistrer le PDF sur le disque
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_buffer.getvalue())

                # Générer l'audio avec ElevenLabs
                audio_name = image.name.rsplit('.', 1)[0] + '.mp3'
                audio_path = os.path.join(settings.MEDIA_ROOT, 'audio', audio_name)
                os.makedirs(os.path.dirname(audio_path), exist_ok=True)

                audio = client.text_to_speech.convert(
                    text=texte,
                    voice_id="pNInz6obpgDQGcFmaJgB",
                    model_id="eleven_multilingual_v2",
                    output_format="mp3_44100_128",
                )

                # Enregistrer l'audio sur le disque
                with open(audio_path, 'wb') as f:
                    for chunk in audio:
                        f.write(chunk)

                # Enregistrer le document dans le modèle Document
                document = Document(
                    type_document=form.cleaned_data.get('type_document', 'autre'),
                    fichier=f'documents/{pdf_name}',
                    uploaded_by=request.user if request.user.is_authenticated else None,
                    etudiant=form.cleaned_data.get('etudiant')
                )
                document.save()

                # Fermer le buffer PDF
                pdf_buffer.close()

                # Supprimer le fichier temporaire
                try:
                    if os.path.exists(image_path):
                        os.remove(image_path)
                except PermissionError as e:
                    print(f"Impossible de supprimer le fichier temporaire : {e}")

                return render(request, 'app/resultat.html', {
                    'document': document,
                    'texte': texte,
                    'audio_url': f'{settings.MEDIA_URL}audio/{audio_name}'
                })
            except Exception as e:
                if os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except PermissionError:
                        print(f"Impossible de supprimer le fichier temporaire : {image_path}")
                print(traceback.format_exc())
                return render(request, 'app/resultat.html', {'texte': f"Erreur : {str(e)}"})
    else:
        form = ImageUploadForm()
    return render(request, 'app/upload.html', {'form': form})