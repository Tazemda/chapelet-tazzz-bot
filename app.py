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

def call_deepseek(prompt, max_tokens=3000, timeout=180):
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
        raise Exception("⏱️ Timeout : DeepSeek n'a pas répondu dans les 180 secondes.")
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

# ================= PROMPT POUR DEEPSEEK (structure exigeante mais concise) =================
PROMPT_JOUR = """
Tu es un expert pédagogique. Domaine : "{domaine}".

Génère le contenu du **Jour {jour_num}** (objectif : {titre_objectif}) pour un chapelet d’apprentissage.

**RÈGLES STRICTES** :
- Commence par écrire le titre : `## **JOUR {jour_num} – [TITRE EN MAJUSCULES, ADAPTÉ]`
- Ensuite, EXACTEMENT 5 DIZAINES (DIZAINE 1 à 5), chacune au format suivant :

**DIZAINE X – Concept : [nom du concept]**

**1) Méditation (gros grain)** : 3 à 5 phrases denses, avec un exemple clair (comme pour le PICO : définition, rôle, application).

**2) Notre Père** : une seule phrase, question centrale qui résout un problème clé.

**3) Je vous salue Marie** (à répéter 10 fois) : 4 à 6 phrases synthétiques, mémorisables, qui résument le concept.

**4) Gloire au Père** (à répéter 3 fois) : "Le concept [nom] est consolidé."

Ne dépasse pas 2500 tokens au total. Soigne la qualité et l’adaptation au domaine.
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
        raw = call_deepseek(prompt, max_tokens=3000, timeout=180)
        contenu = clean_markdown(raw)
        # Vérification que le titre est présent
        if not re.search(r'##\s*\*\*JOUR\s+\d+', contenu, re.IGNORECASE):
            contenu = f"## **JOUR {jour_num} – {titre_objectif.upper()}**\n\n{contenu}"
        return contenu
    except Exception as e:
        # On renvoie l'erreur directement pour que l'utilisateur voie le vrai problème
        return f"❌ **Erreur DeepSeek** : {str(e)}\n\nVeuillez vérifier votre clé API, votre crédit, ou réessayer plus tard."

# ================= MODE PERSONNEL (utilise aussi DeepSeek) =================
def generer_personnel(defauts):
    notre_pere = "Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes."
    resultats = []
    for i, d in enumerate(defauts, 1):
        prompt = f"""
Génère un **Mystère {i}** pour le défaut : "{d}".
Structure :
**Mystère {i} – {d}**
**Méditation** : (rappel d’un échec passé + visualisation positive, 2-3 phrases)
**Notre Père** : "{notre_pere}" (à répéter 3 fois)
**Je vous salue Marie** : (une phrase courte positive qui corrige ce défaut, à répéter 10 fois)
**Gloire au Père** : "Je remercie Dieu et l'univers pour cette transformation." (à répéter 3 fois)
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
