import os
import re
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tazbot-secret-key")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

def call_deepseek(prompt, max_tokens=6000, timeout=240, retries=2):
    if not DEEPSEEK_API_KEY:
        raise Exception("❌ Clé API manquante")
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": max_tokens
    }
    for attempt in range(retries + 1):
        try:
            resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            else:
                raise Exception(f"API error {resp.status_code}: {resp.text[:200]}")
        except requests.exceptions.Timeout:
            if attempt < retries:
                continue
            raise Exception("⏱️ Timeout")
        except Exception as e:
            if attempt < retries:
                continue
            raise e

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

# ================= PROMPT POUR GÉNÉRER LES 7 JOURS EN UNE FOIS =================
PROMPT_COMPLET = """
Tu es un expert pédagogique. L'utilisateur souhaite apprendre le domaine suivant : "{domaine}".

Génère un programme complet de 7 jours (un chapelet d'apprentissage). Pour chaque jour (Jour 1 à Jour 7), tu dois produire :

- Un titre adapté au domaine sous la forme : `## **JOUR X – [TITRE EN MAJUSCULES]`
- Exactement 5 DIZAINES, chacune avec les sections suivantes (utilise ces intitulés exacts) :

**DIZAINE X – Concept : [nom du concept]**

**Méditation synthèse générale (gros grain)**
(3-5 phrases denses avec exemples)

**Notre Père** (répète ceci 3 x – pas de graines)
(une seule phrase : question centrale)

**Je vous salue Marie** (répète ceci 10 x – les 10 petites graines)
(paragraphe de 5-8 phrases synthétiques)

**Gloire au Père** (répète ceci 3 x)
"Le concept [nom] est consolidé."

Structure le texte avec des séparateurs clairs entre les jours (par exemple `--- Jour 1 ---`). Le contenu doit être directement utilisable.

Soigne la qualité, adapte parfaitement au domaine. Ne mets pas d'instructions de répétition dans le texte.
"""

def generer_chapelet_complet(domaine):
    prompt = PROMPT_COMPLET.format(domaine=domaine)
    raw = call_deepseek(prompt, max_tokens=6500, timeout=300, retries=2)
    return clean_markdown(raw)

# ================= MODE PERSONNEL (inchangé) =================
def generer_personnel(defauts):
    notre_pere = "Mon cerveau, par sa plasticité infinie, se réorganise chaque jour."
    resultats = []
    for i, d in enumerate(defauts, 1):
        prompt = f"Mystère {i} – {d}\n**Méditation** : souvenir d'un échec puis visualisation positive.\n**Notre Père** : {notre_pere} (3 fois)\n**Je vous salue Marie** : phrase courte positive corrigeant {d} (10 fois)\n**Gloire au Père** : Merci (3 fois)"
        try:
            raw = call_deepseek(prompt, max_tokens=500)
            resultats.append(clean_markdown(raw))
        except:
            resultats.append(f"**Mystère {i} – {d}** (version de secours)")
    return "\n\n".join(resultats)

# ================= ROUTES =================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generer_expertise', methods=['POST'])
def generer_expertise_route():
    data = request.get_json()
    domaine = data.get('domaine')
    if not domaine:
        return jsonify({'error': 'Domaine requis'}), 400
    try:
        chapelet_complet = generer_chapelet_complet(domaine)
        # On découpe les jours (on suppose que le modèle utilise "--- Jour X ---" comme séparateur)
        import re
        jours = re.split(r'---\s*Jour\s+\d+\s*---', chapelet_complet)
        # Nettoie et renvoie la liste des jours
        jours_clean = []
        for j in jours:
            j = j.strip()
            if j:
                jours_clean.append(j)
        # Si on n'a pas 7 jours, on ajuste
        if len(jours_clean) != 7:
            # fallback: on renvoie le texte complet
            return jsonify({'chapelet': chapelet_complet, 'structure': 'texte_unique'})
        return jsonify({'jours': jours_clean})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
