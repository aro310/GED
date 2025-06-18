import pytesseract
from PIL import Image

def extraire_texte_depuis_image(image_path):
    try:
        with Image.open(image_path) as img:
            texte = pytesseract.image_to_string(img, lang='fra')
        return texte.strip() or "Aucun texte extrait"
    except Exception as e:
        return f"Erreur OCR : {str(e)}"