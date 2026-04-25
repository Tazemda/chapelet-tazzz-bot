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

def call_deepseek(prompt, max_tokens=1800):
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
        resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=120)
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

# PROMPT COURT pour générer uniquement les 5 dizaines d'un jour
PROMPT_JOUR = """
Tu es un expert pédagogique. Domaine: "{domaine}". Jour {jour_num}: {titre_jour}.

Génère 5 DIZAINES exactement comme suit (ne mets pas de titre général) :

**DIZAINE 1 – Concept : [nom]**
**1) Méditation** : (un paragraphe dense avec définitions, exemples, points clés)
**2) Notre Père** : (une question problématique)
**3) Je vous salue Marie** : (un paragraphe synthétique de plusieurs phrases)
**4) Gloire au Père** : "Le concept [nom] est consolidé."

(répète pour DIZAINE 2 à 5)

Contenu adapté au domaine. Commence par "**DIZAINE 1**". Pas de texte avant.
"""

def generer_jour_expertise(domaine, jour_num):
    titres_jours = [
        "Découverte des bases fondamentales",
        "Approfondissement des pratiques clés",
        "Cas complexes et exceptions",
        "Contrôle qualité et indicateurs",
        "Gestion des risques et plan d'action",
        "Synthèse et liens entre concepts",
        "Auto‑évaluation et perfectionnement"
    ]
    titre_jour = titres_jours[jour_num-1]
    try:
        prompt = PROMPT_JOUR.format(domaine=domaine, jour_num=jour_num, titre_jour=titre_jour)
        raw = call_deepseek(prompt, max_tokens=1800)
        contenu = clean_markdown(raw)
        return f"## {titre_jour}\n\n{contenu}"
    except Exception as e:
        print(f"Erreur jour {jour_num}: {e}")
        return f"""## {titre_jour}
**DIZAINE 1 – Introduction à {domaine}**
**1) Méditation** : {domaine} nécessite une prévention adaptée. Exemple : triade de Virchow.
**2) Notre Père** : Quels sont les trois facteurs de risque ?
**3) Je vous salue Marie** : Je retiens les piliers de la prévention.
**4) Gloire au Père** : Consolidé.

(Dizaines 2 à 5 similaires – contenu généré par API normalement.)"""

# ---------- PERSONNEL (inchangé, peut être simplifié) ----------
def generer_personnel(defauts):
    notre_pere = "Mon cerveau, par sa plasticité infinie, se réorganise chaque jour."
    mysteres = []
    for i, d in enumerate(defauts, 1):
        prompt = f"Mystère {i} – {d}\n**Méditation** : souvenir d'échec + visualisation positive.\n**Notre Père** : {notre_pere} (3 fois)\n**Je vous salue Marie** : phrase courte corrigeant {d} (10 fois)\n**Gloire au Père** : Merci (3 fois)"
        try:
            raw = call_deepseek(prompt, max_tokens=400)
            mysteres.append(clean_markdown(raw))
        except:
            mysteres.append(f"**Mystère {i} – {d}**\nMéditation ...\nNotre Père ...\nAve Maria ...")
    return "\n\n".join(mysteres)

# ---------- ROUTES ----------
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
