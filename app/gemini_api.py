# app/gemini_api.py

import google.generativeai as genai

# Configurez votre clé API
GOOGLE_API_KEY = "AIzaSyBgZqucc4f1QQo4VyHpmUxhsy5U29Y4_MY"
genai.configure(api_key=GOOGLE_API_KEY)

# Initialisez le modèle
model = genai.GenerativeModel('gemma-3-27b-it')  # Ajuste selon ton besoin

def chat_with_gemini(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erreur: {e}"
