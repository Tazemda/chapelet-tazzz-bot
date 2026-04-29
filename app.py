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

def call_deepseek(prompt, max_tokens=2500):
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
        resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=150)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"API error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        raise Exception(f"Erreur API: {str(e)}")

def clean_markdown(text):
    text = re.sub(r'```[\s\S]*?```', '', text)
    return text.replace('`', '').strip()

def remove_markdown_chars(text):
    text = re.sub(r'\*\*', '', text)
    text = re.sub(r'\*', '', text)
    text = re.sub(r'#', '', text)
    return text

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

# ================= EXPERTISE CLASSIQUE (7 jours) =================
PROMPT_JOUR = """
Tu es un expert pédagogique. Domaine : "{domaine}".

Génère le contenu complet du **Jour {jour_num}** sur 7 jours.  
L'objectif général du jour {jour_num} est : {titre_objectif}.

Commence par le titre : `## **JOUR {jour_num} : [TITRE PERTINENT EN MAJUSCULES, ADAPTÉ AU DOMAINE]**`

Puis, EXACTEMENT 5 DIZAINES. Chaque dizaine doit suivre ce format (concis) :

**DIZAINE X : CONCEPT : [nom du concept]**

A) **Synthèse générale Méditation à lire en tenant un gros grain du chapelet** : exactement 8 phrases moyennement denses non numérotés (toutes les méditations, tous les jours) : définition + rôle + exemple court.

B) A la place du **Notre Père**, écrire : RÉPÈTE 3 fois sans égrener le chapelet : une seule phrase, question centrale.

C) A la place du **Je vous salue Marie**, écrire : RÉPÈTE 10 fois en égrenant 10 petits grains: exactement 6 phrases (toutes les méditations, tous les jours) synthétiques, numérotées et mémorisables.

D) A la place du **Gloire au Père**, écrire : RÉPÈTE 3 fois sans égrener: "Le concept [nom] est consolidé."

Soigne la qualité. Ne dépasse pas 2000 tokens au total.
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
        raw = call_deepseek(prompt, max_tokens=2000)
        contenu = clean_markdown(raw)
        contenu = remove_markdown_chars(contenu)
        if not re.search(r'JOUR\s+\d+', contenu, re.IGNORECASE):
            contenu = f"JOUR {jour_num} – {titre_objectif.upper()}\n\n{contenu}"
        return contenu
    except Exception as e:
        print(f"Erreur jour {jour_num}: {e}")
        return f"JOUR {jour_num} – {titre_objectif.upper()} (version de secours)\n\n(erreur technique, veuillez réessayer)"

# ================= COURS (6 CHAPITRES) =================
PROMPT_CHAPITRE_JOUR = """
Tu es un expert pédagogique. Tu reçois le texte d'un chapitre (environ 3 pages A4).
Transforme ce chapitre en un contenu structuré pour une journée d'étude (5 dizaines).

Voici le texte du chapitre :

{texte_chapitre}

Génère le contenu du **Jour {jour_num}** selon le format exact suivant :

## **JOUR {jour_num} : [TITRE ADAPTÉ AU CHAPITRE]**

**DIZAINE 1 : CONCEPT : [nom]**
A) **Méditation** : 8 phrases (définition, rôle, exemple court).
B) **Notre Père** : une question centrale (RÉPÈTE 3 fois).
C) **Je vous salue Marie** : 6 phrases numérotées (RÉPÈTE 10 fois).
D) **Gloire au Père** : "Le concept [nom] est consolidé." (RÉPÈTE 3 fois)

(même structure pour DIZAINE 2 à 5)

Soigne la qualité, reste fidèle au texte source. Ne dépasse pas 2500 tokens.
"""

PROMPT_JOUR_7 = """
Tu es un expert pédagogique. L'utilisateur a étudié 6 chapitres. Génère un **jour de révision et d'évaluation** (5 dizaines) sous forme de questions et exercices.

Les chapitres sont :
{chapitres_titres}

Crée le contenu du **Jour 7 – RÉVISION ET CONTRÔLE DES CONNAISSANCES** avec 5 dizaines :
- Dizaine 1 : QCM sur le chapitre 1
- Dizaine 2 : QCM sur le chapitre 2
- …
- Dizaine 5 : questions ouvertes transversales

Format identique à l'expertise (Méditation, Notre Père, Ave Maria, Gloire). Soigne la pédagogie.
"""

@app.route('/generer_chapitre', methods=['POST'])
def generer_chapitre_route():
    """Génère le contenu d'un chapitre (jour) à partir de son texte brut."""
    data = request.get_json()
    texte = data.get('texte')
    num = data.get('num')
    if not texte or not num:
        return jsonify({'error': 'Texte et numéro requis'}), 400
    prompt = PROMPT_CHAPITRE_JOUR.format(texte_chapitre=texte, jour_num=num)
    contenu = call_deepseek(prompt, max_tokens=2500)
    contenu = clean_markdown(contenu)
    contenu = remove_markdown_chars(contenu)
    return jsonify({'contenu': contenu})

@app.route('/generer_jour7', methods=['POST'])
def generer_jour7_route():
    """Génère le jour 7 à partir des titres des 6 chapitres."""
    data = request.get_json()
    titres = data.get('titres', [f"Chapitre {i}" for i in range(1,7)])
    prompt = PROMPT_JOUR_7.format(chapitres_titres="\n".join(titres))
    contenu = call_deepseek(prompt, max_tokens=2500)
    contenu = clean_markdown(contenu)
    contenu = remove_markdown_chars(contenu)
    return jsonify({'contenu': contenu})

# ================= ROUTES COMMUNES =================
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
