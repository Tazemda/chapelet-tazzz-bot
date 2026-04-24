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

def call_deepseek(prompt):
    if not DEEPSEEK_API_KEY:
        raise Exception("Clé API DeepSeek manquante")
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 3000
    }
    resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=90)
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"API error {resp.status_code}: {resp.text[:200]}")

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

def generer_jour(domaine, jour_num):
    objectifs = [
        "Découvrir les bases fondamentales",
        "Approfondir les pratiques clés",
        "Gérer les cas complexes et exceptions",
        "Mettre en place des indicateurs de contrôle",
        "Anticiper et gérer les risques",
        "Faire la synthèse et les liens entre concepts",
        "S'auto-évaluer et se perfectionner"
    ]
    titre_jour = objectifs[jour_num-1]
    prompt = f"""
Génère le contenu du **Jour {jour_num}** d'un chapelet d'apprentissage sur le domaine : "{domaine}".
Objectif de ce jour : {titre_jour}.

Pour ce jour, invente **5 concepts** (DIZAINE 1 à 5) et pour chaque concept, écris :

- **1) Méditation (grande fiche)** : un paragraphe dense (définitions, exemples concrets, points clés).
- **2) Notre Père** : une question problématique (à répéter 3 fois).
- **3) Je vous salue Marie** : un paragraphe synthétique (à répéter 10 fois).
- **4) Gloire au Père** : une phrase de consolidation.

Format exact :
**DIZAINE 1 – Concept : [nom]**
**1) Méditation** ...  
**2) Notre Père** ...  
**3) Je vous salue Marie** ...  
**4) Gloire au Père** ...

Fais 5 dizaines. Adapte au domaine "{domaine}". Commence par "**DIZAINE 1**".
"""
    raw = call_deepseek(prompt)
    raw = clean_markdown(raw)
    return f"--- Jour {jour_num} – {titre_jour} ---\n\n{raw}"

# ---------- Routes ----------
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
    try:
        contenu = generer_jour(domaine, int(jour))
        return jsonify({'contenu': contenu})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
