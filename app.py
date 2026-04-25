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

def call_deepseek(prompt, max_tokens=3500, timeout=180):
    if not DEEPSEEK_API_KEY:
        raise Exception("❌ Clé API DeepSeek manquante. Ajoutez DEEPSEEK_API_KEY dans Render.")
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
            # Essayer d'obtenir le message d'erreur lisible
            try:
                error = resp.json().get("error", {}).get("message", "Erreur inconnue")
            except:
                error = resp.text[:200]
            raise Exception(f"HTTP {resp.status_code}: {error}")
    except requests.exceptions.Timeout:
        raise Exception("⏱️ Timeout – DeepSeek met trop de temps. Réessayez.")
    except Exception as e:
        raise Exception(f"❌ {str(e)}")

def clean_markdown(text):
    text = re.sub(r'```[\s\S]*?```', '', text)
    return text.replace('`', '').strip()

# Base de données pour les feedbacks
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

# ================= PROMPT D'EXPERTISE (STABLE) =================
PROMPT_JOUR = """
Tu es un expert pédagogique. L'utilisateur veut apprendre le domaine suivant : "{domaine}".

Génère le contenu du **Jour {jour_num}** (objectif : {objectif}) pour un chapelet d'apprentissage de 7 jours.

**RÈGLES IMPORTANTES** :
- NE PARLE PAS de médicament, d'essai clinique ou d'AMM, sauf si le domaine mentionne explicitement ces termes.
- Le titre du jour doit être adapté au domaine : `## **JOUR {jour_num} – [TITRE PERTINENT EN MAJUSCULES]`
- Ensuite, écris 5 DIZAINES au format exact suivant :

**DIZAINE X – Concept : [nom du concept]**

**Méditation synthèse générale (gros grain)** : (3 à 5 phrases denses, avec un exemple clair – définition, rôle, application)

**Notre Père** (répète ceci 3 x – pas de graines) : (une seule phrase : une question centrale qui montre le problème clé que ce concept résout)

**Je vous salue Marie** (répète ceci 10 x – les 10 petites graines) : (un paragraphe de 5 à 8 phrases, synthétique et mémorisable)

**Gloire au Père** (répète ceci 3 x) : (une phrase courte : "Le concept [nom] est consolidé.")

Soigne la qualité. Ne mets pas de "à répéter" dans le texte, c'est l'utilisateur qui applique.
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
    objectif = objectifs[jour_num-1]
    prompt = PROMPT_JOUR.format(domaine=domaine, jour_num=jour_num, objectif=objectif)
    try:
        raw = call_deepseek(prompt, max_tokens=3600, timeout=180)
        contenu = clean_markdown(raw)
        # Vérifie et corrige le titre si absent
        if not re.search(r'##\s*\*\*JOUR\s+\d+', contenu, re.IGNORECASE):
            contenu = f"## **JOUR {jour_num} – {objectif.upper()}**\n\n{contenu}"
        return contenu
    except Exception as e:
        return f"❌ **Erreur DeepSeek** : {str(e)}\\n\\nVérifiez votre clé API et votre crédit."

# ================= MODE PERSONNEL =================
def generer_personnel(defauts):
    notre_pere = "Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes."
    resultats = []
    for i, d in enumerate(defauts, 1):
        prompt = f"""
Génère un **Mystère {i}** pour le défaut : "{d}".
Format exact :
**Mystère {i} – {d}**
**Méditation synthèse générale (gros grain)** : (2-3 phrases : rappel d'un échec passé puis visualisation positive)
**Notre Père** (répète ceci 3 x) : "{notre_pere}"
**Je vous salue Marie** (répète ceci 10 x) : (une phrase courte positive adaptée à ce défaut)
**Gloire au Père** (répète ceci 3 x) : "Je remercie Dieu et l'univers pour cette transformation."
"""
        try:
            raw = call_deepseek(prompt, max_tokens=700, timeout=90)
            resultats.append(clean_markdown(raw))
        except Exception as e:
            resultats.append(f"❌ **Erreur pour le défaut {i}** : {str(e)}")
    return "\n\n".join(resultats)

# ================= ROUTES =================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generer_jour_expertise', methods=['POST'])
def generer_jour_expertise_route():
    data = request.get_json()
    domaine = data.get('domaine')
    jour = data.get('jour')
    if not domaine or not jour:
        return jsonify({'error': 'Domaine et jour requis'}), 400
    contenu = generer_jour_expertise(domaine, int(jour))
    return jsonify({'contenu': contenu})

@app.route('/generer_personnel', methods=['POST'])
def generer_personnel_route():
    data = request.get_json()
    defauts = data.get('defauts')
    if not defauts or len(defauts) != 5:
        return jsonify({'error': '5 défauts requis'}), 400
    contenu = generer_personnel(defauts)
    return jsonify({'contenu': contenu})

@app.route('/feedback', methods=['POST'])
def feedback():
    data = request.get_json()
    note = data.get('note')
    commentaire = data.get('commentaire')
    if note is None or commentaire is None:
        return jsonify({'error': 'Note et commentaire requis'}), 400
    conn = sqlite3.connect('tazbot.db')
    c = conn.cursor()
    c.execute("INSERT INTO feedback (date, note, commentaire) VALUES (?, ?, ?)",
              (str(datetime.now()), note, commentaire))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
