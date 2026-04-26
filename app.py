import os
import re
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tazbot-secret-key")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

def call_deepseek(prompt, max_tokens=3500, timeout=200):
    if not DEEPSEEK_API_KEY:
        raise Exception("Clé API manquante")
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": max_tokens
    }
    try:
        resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"API error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        raise Exception(f"Erreur API: {str(e)}")

def clean_markdown(text):
    text = re.sub(r'```[\s\S]*?```', '', text)
    return text.replace('`', '').strip()

def init_db():
    conn = sqlite3.connect('tazbot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS feedback
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT,
                  note INTEGER,
                  commentaire TEXT)''')
    conn.commit()
    conn.close()
init_db()

PROMPT_JOUR = """
Tu es un expert pédagogique. Domaine : "{domaine}".

Génère le contenu complet du **Jour {jour_num}** sur 7 jours.  
L'objectif général du jour {jour_num} est : {titre_objectif}.

Commence par écrire le **titre du jour** sous la forme (obligatoire) :
## **JOUR {jour_num} – [TITRE PERTINENT EN MAJUSCULES, ADAPTÉ AU DOMAINE]**

Puis, rédige exactement **5 DIZAINES** selon le modèle ci‑dessous.  
Chaque dizaine doit être complète et détaillée.

**DIZAINE X – Concept : [nom du concept]**
**Méditation synthèse générale (gros grain)** : (paragraphe dense avec définitions, exemples concrets, points clés)
**Notre Père** (répète ceci 3 x – pas de graines) : (une seule phrase : une question centrale pertinente qui montre le problème clé que ce concept résout)
**Je vous salue Marie** (répète ceci 10 x – les 10 petites graines) : (un paragraphe de 5 à 8 phrases, synthétique et mémorisable)
**Gloire au Père** (répète ceci 3 x) : (une phrase courte de consolidation : "Le concept [nom] est consolidé.")

Répète pour **DIZAINE 2** à **DIZAINE 5**.

Soigne la qualité et l'exhaustivité. Contenu directement utilisable pour un apprentissage autonome.
"""

def generer_jour_expertise(domaine, jour_num):
    objectifs = [
        "Découverte des bases fondamentales",
        "Approfondissement des pratiques clés",
        "Cas complexes et exceptions",
        "Contrôle qualité et indicateurs",
        "Gestion des risques et plan d'action",
        "Synthèse et liens entre concepts",
        "Auto‑évaluation et perfectionnement"
    ]
    titre_objectif = objectifs[jour_num-1]
    prompt = PROMPT_JOUR.format(domaine=domaine, jour_num=jour_num, titre_objectif=titre_objectif)

    # Tentative avec tokens augmentés
    try:
        raw = call_deepseek(prompt, max_tokens=3800, timeout=240)
        # Vérification du nombre de dizaines
        if raw.count("**DIZAINE") < 5:
            # Deuxième tentative avec encore plus de tokens
            raw = call_deepseek(prompt, max_tokens=4500, timeout=280)
        contenu = clean_markdown(raw)
        if not re.search(r'##\s*\*\*JOUR\s+\d+', contenu, re.IGNORECASE):
            contenu = f"## **JOUR {jour_num} – {titre_objectif.upper()}**\n\n{contenu}"
        return contenu
    except Exception as e:
        print(f"Erreur jour {jour_num}: {e}")
        return f"""## **JOUR {jour_num} – {titre_objectif.upper()}** (version de secours)

**DIZAINE 1 – Introduction à {domaine}**
**Méditation synthèse générale (gros grain)** : (contenu temporaire – veuillez réessayer plus tard)
**Notre Père** (répète ceci 3 x – pas de graines) : ?
**Je vous salue Marie** (répète ceci 10 x – les 10 petites graines) : ...
**Gloire au Père** (répète ceci 3 x) : consolidé.
(Dizaines 2 à 5 structure similaire)"""

# (les autres fonctions (personnel, routes) sont inchangées – gardez votre version)
