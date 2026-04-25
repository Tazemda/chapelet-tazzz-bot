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

def call_deepseek(prompt, max_tokens=1500):
    if not DEEPSEEK_API_KEY:
        raise Exception("Clé API manquante")
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": max_tokens
    }
    resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=120)
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"API error {resp.status_code}: {resp.text[:200]}")

def clean_markdown(text):
    return re.sub(r'```[\s\S]*?```', '', text).replace('`', '').strip()

# ------------------ BASE DE DONNÉES ------------------
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

# ------------------ PROMPT OPTIMISÉ (5 dizaines, concis) ------------------
PROMPT_JOUR = """
Domaine: "{domaine}". Jour {jour_num} – {objectif}.

Génère d'abord un titre percutant :
## **JOUR {jour_num} – [TITRE EN MAJUSCULES ADAPTÉ AU DOMAINE]**

Puis, exactement 5 DIZAINES. Chaque dizaine suit ce format court mais complet :

**DIZAINE X – Concept : [nom]**
**1) Méditation** : (2-3 phrases : définition, exemple, point clé)
**2) Notre Père** : (une question)
**3) Je vous salue Marie** : (1-2 phrases synthétiques)
**4) Gloire au Père** : "Le concept [nom] est consolidé."

Ne dépasse pas 5 dizaines. Soigne l'adaptation au domaine.
"""

OBJECTIFS = [
    "Découverte des bases",
    "Approfondissement pratique",
    "Cas complexes",
    "Contrôle et indicateurs",
    "Gestion des risques",
    "Synthèse",
    "Auto-évaluation"
]

def generer_jour(domaine, jour_num):
    obj = OBJECTIFS[jour_num-1]
    prompt = PROMPT_JOUR.format(domaine=domaine, jour_num=jour_num, objectif=obj)
    try:
        raw = call_deepseek(prompt, max_tokens=1500)
        contenu = clean_markdown(raw)
        if not contenu.startswith("## **JOUR"):
            contenu = f"## **JOUR {jour_num} – {obj.upper()}**\n\n{contenu}"
        return contenu
    except Exception as e:
        return f"""## **JOUR {jour_num} – {obj.upper()}** (mode dégradé)
**DIZAINE 1 – Introduction à {domaine}**
**1) Méditation** : (contenu temporaire)
**2) Notre Père** : ?
**3) Je vous salue Marie** : ...
**4) Gloire au Père** : consolidé.
(Dizaines 2 à 5 similaires)"""

# ------------------ PERSONNEL ------------------
def generer_personnel(defauts):
    notre_pere = "Mon cerveau, par sa plasticité, se réorganise chaque jour."
    resultats = []
    for i, d in enumerate(defauts, 1):
        prompt = f"Mystère {i} – {d}\nMéditation : souvenir + visualisation positive\nNotre Père : {notre_pere} (3 fois)\nJe vous salue Marie : phrase courte positive (10 fois)\nGloire : Merci (3 fois)"
        try:
            raw = call_deepseek(prompt, max_tokens=400)
            resultats.append(clean_markdown(raw))
        except:
            resultats.append(f"**Mystère {i} – {d}**\n(version simplifiée)")
    return "\n\n".join(resultats)

# ------------------ ROUTES ------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generer_jour', methods=['POST'])
def generer_jour_route():
    data = request.get_json()
    domaine = data.get('domaine')
    jour = data.get('jour')
    if not domaine or not jour:
        return jsonify({'error': 'Domaine et jour requis'}), 400
    contenu = generer_jour(domaine, int(jour))
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
