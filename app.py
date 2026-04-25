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

def call_deepseek(prompt, max_tokens=3500, timeout=240):
    if not DEEPSEEK_API_KEY:
        raise Exception("❌ Clé API DeepSeek manquante. Ajoutez DEEPSEEK_API_KEY dans les variables d'environnement.")
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
    except requests.exceptions.Timeout:
        raise Exception("⏱️ Timeout : DeepSeek n'a pas répondu dans le temps imparti. Réessayez plus tard.")
    except Exception as e:
        raise Exception(f"❌ Erreur API: {str(e)}")

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

# ================= PROMPT POUR EXPERTISE (libellés exacts) =================
PROMPT_JOUR = """
Tu es un expert pédagogique. Domaine : "{domaine}".

Génère le contenu complet du **Jour {jour_num}** (objectif : {titre_objectif}) pour un chapelet d'apprentissage.

**RÈGLES STRICTES** :
- Commence par le titre : `## **JOUR {jour_num} – [TITRE EN MAJUSCULES, ADAPTÉ AU DOMAINE]**`
- Ensuite, EXACTEMENT 5 DIZAINES (DIZAINE 1 à 5). Chaque DIZAINE doit suivre ce format (sans mention "à répéter" ni "graines") :

**DIZAINE X – Concept : [nom du concept]**

**1) Méditation (gros grain)** : (3 à 5 phrases denses, avec un exemple clair – définition, rôle, application)

**2) Notre Père** : (une seule phrase : une question centrale pertinente qui montre le problème clé que ce concept résout)

**3) Je vous salue Marie** : (un paragraphe de 5 à 8 phrases, synthétique et mémorisable, qui résume le concept)

**4) Gloire au Père** : (une phrase courte de consolidation : "Le concept [nom] est consolidé.")

Soigne la qualité pédagogique. Adapte parfaitement au domaine "{domaine}".
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
    try:
        raw = call_deepseek(prompt, max_tokens=3500, timeout=240)
        contenu = clean_markdown(raw)
        # Vérifie que le titre est présent
        if not re.search(r'##\s*\*\*JOUR\s+\d+', contenu, re.IGNORECASE):
            contenu = f"## **JOUR {jour_num} – {titre_objectif.upper()}**\n\n{contenu}"
        return contenu
    except Exception as e:
        return f"❌ **Erreur de génération** : {str(e)}\n\nVeuillez vérifier votre clé API et votre crédit DeepSeek."

# ================= MODE PERSONNEL (simplifié mais utilisant DeepSeek) =================
def generer_personnel(defauts):
    notre_pere = "Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes."
    resultats = []
    for i, d in enumerate(defauts, 1):
        prompt = f"""
Génère un **Mystère {i}** pour le défaut : "{d}".
Format exact :
**Mystère {i} – {d}**
**Méditation** : (2-3 phrases : rappel d'un échec passé puis visualisation positive)
**Notre Père** : "{notre_pere}"
**Je vous salue Marie** : une phrase courte positive adaptée à ce défaut
**Gloire au Père** : "Je remercie Dieu et l'univers pour cette transformation."
"""
        try:
            raw = call_deepseek(prompt, max_tokens=600, timeout=90)
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
