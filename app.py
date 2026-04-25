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

def call_deepseek(prompt, max_tokens=4000):   # augmenté à 4000
    if not DEEPSEEK_API_KEY:
        raise Exception("Clé API DeepSeek manquante")
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
        raise Exception(f"Erreur appel API: {str(e)}")

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

# ------------------ EXPERTISE ------------------
OBJECTIFS_JOURS = [
    "Découverte des bases fondamentales",
    "Approfondissement des pratiques clés",
    "Cas complexes et exceptions",
    "Contrôle qualité et indicateurs",
    "Gestion des risques et plan d'action",
    "Synthèse et liens entre concepts",
    "Auto‑évaluation et perfectionnement"
]

PROMPT_JOUR = """
Génère le contenu du **Jour {jour_num}** d’un chapelet d’apprentissage sur le domaine: "{domaine}".
Objectif: {titre_jour}. Crée 5 concepts (DIZAINE 1 à 5). Pour chaque concept, utilise ce format exact:

**DIZAINE X – Concept : [nom]**

**1) Méditation (grande fiche)**  
*Instruction: Tenez le gros grain. Lisez ce paragraphe.*  
(Paragraphe dense: définitions, exemples, points clés.)

**2) Notre Père**  
*Récitez cette question 3 fois.*  
« Question problématique sur le concept »

**3) Je vous salue Marie**  
*Répétez ce paragraphe 10 fois.*  
(Paragraphe synthétique de plusieurs phrases.)

**4) Gloire au Père**  
*Récitez 3 fois.*  
« Le concept "[nom]" est consolidé. »

Adapte au domaine "{domaine}". Commence par "**DIZAINE 1**". Ne mets pas de titre avant.
"""

def generer_jour_expertise(domaine, jour_num):
    titre_jour = OBJECTIFS_JOURS[jour_num-1]
    prompt = PROMPT_JOUR.format(domaine=domaine, jour_num=jour_num, titre_jour=titre_jour)
    raw = call_deepseek(prompt, max_tokens=4000)
    raw = clean_markdown(raw)
    return f"--- Jour {jour_num} – {titre_jour} ---\n\n{raw}"

# ------------------ PERSONNEL (inchangé, mais gardé) ------------------
def generer_personnel(defauts):
    notre_pere = "Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes. Je choisis ma lucidité."
    mysteres = []
    for i, defaut in enumerate(defauts, 1):
        prompt = f"""
Génère le **Mystère {i} – {defaut}** pour un chapelet de développement personnel.
Structure:
**Méditation** : (une courte visualisation : rappel d'une situation passée nuisible + nouvelle attitude positive)
**Notre Père** : {notre_pere} *(3 fois)*
**Je vous salue Marie** : (une phrase courte positive corrigeant ce défaut) *(10 fois)*
**Gloire au Père** : "Je remercie Dieu et l'univers pour cette transformation." *(3 fois)*
"""
        try:
            raw = call_deepseek(prompt, max_tokens=800)
            mysteres.append(clean_markdown(raw))
        except:
            mysteres.append(f"**Mystère {i} – {defaut}**\n**Méditation** : Je visualise le dépassement de ce défaut.\n**Notre Père** : {notre_pere}\n**Je vous salue Marie** : Je transforme {defaut} en force.\n**Gloire au Père** : Merci.")
    chapelet = f"""
**CHAPELET TAZZZ BOT – MODE DÉVELOPPEMENT PERSONNEL (21/66 jours)**

> Munissez-vous d'un chapelet pour égrener chaque grain...

### DÉBUT
- Signe de croix : "Au nom de mon engagement, de ma lucidité et de ma persévérance."
- Crucifix : "Je ne subis plus ma vie."
- 3 Ave initiaux : (donnés)
- Gloire : "Je rends grâce."

### 5 MYSTÈRES
""" + "\n\n".join(mysteres) + """

### FIN
- Salve Regina : "..."
- Mantra final : "..."
- Signe de croix final.

Chapelet Tazzz Bot – Plasticité cérébrale – © Dr Tazemda
"""
    return chapelet

# ------------------ ROUTES ------------------
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
    try:
        contenu = generer_jour_expertise(domaine, int(jour))
        return jsonify({'contenu': contenu})
    except Exception as e:
        print("Erreur:", e)
        return jsonify({'error': str(e)}), 500

@app.route('/generer_personnel', methods=['POST'])
def generer_personnel_route():
    data = request.get_json()
    defauts = data.get('defauts')
    if not defauts or len(defauts) != 5:
        return jsonify({'error': '5 défauts requis'}), 400
    try:
        contenu = generer_personnel(defauts)
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
