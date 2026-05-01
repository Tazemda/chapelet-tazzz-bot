import os
import re
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template, session
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tazbot-secret-key")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# ================= BASE DE DONNÉES UTILISATEURS =================
def init_users_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  pseudo TEXT UNIQUE NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  created_at TEXT)''')
    conn.commit()
    conn.close()
init_users_db()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentification requise'}), 401
        return f(*args, **kwargs)
    return decorated

# ================= FONCTIONS IA =================
def call_deepseek(prompt, max_tokens=3000):
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
        resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=180)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"API error {resp.status_code}: {resp.text[:500]}")
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

# ================= PROMPTS =================
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

(même structure pour DIZAINE 2 à 5)

Soigne la qualité. Ne dépasse pas 2500 tokens au total.
"""

PROMPT_CHAPITRE_JOUR = """
Tu es un expert pédagogique. Tu reçois le texte d'un chapitre (environ 3 pages A4).
Transforme ce chapitre en un contenu structuré pour une journée d'étude (5 dizaines).

Voici le texte du chapitre :

{texte_chapitre}

Génère le contenu du **Jour {jour_num}** selon le format exact suivant :

## **JOUR {jour_num} : [TITRE ADAPTÉ AU CHAPITRE]**

**DIZAINE 1 : CONCEPT : [nom]**
A) **Synthèse générale Méditation à lire en tenant un gros grain du chapelet** : exactement 8 phrases moyennement denses non numérotés (toutes les méditations, tous les jours) : définition + rôle + exemple court.

B) A la place du **Notre Père**, écrire : RÉPÈTE 3 fois sans égrener le chapelet : une seule phrase, question centrale.

C) A la place du **Je vous salue Marie**, écrire : RÉPÈTE 10 fois en égrenant 10 petits grains: exactement 6 phrases (toutes les méditations, tous les jours) synthétiques, numérotées et mémorisables.

D) A la place du **Gloire au Père**, écrire : RÉPÈTE 3 fois sans égrener: "Le concept [nom] est consolidé."

(même structure pour DIZAINE 2 à 5)

Soigne la qualité, reste fidèle au texte source. Ne dépasse pas 2800 tokens.
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
        raw = call_deepseek(prompt, max_tokens=3000)
        contenu = clean_markdown(raw)
        contenu = remove_markdown_chars(contenu)
        if not re.search(r'JOUR\s+\d+', contenu, re.IGNORECASE):
            contenu = f"JOUR {jour_num} – {titre_objectif.upper()}\n\n{contenu}"
        return contenu
    except Exception as e:
        print(f"Erreur jour {jour_num}: {e}")
        return f"JOUR {jour_num} – {titre_objectif.upper()} (version de secours)\n\n(erreur technique: {str(e)})"

# ================= ROUTES D'AUTH SIMPLIFIÉES =================
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    pseudo = data.get('pseudo')
    email = data.get('email')
    password = data.get('password')
    password_confirm = data.get('password_confirm')
    
    if not all([pseudo, email, password, password_confirm]):
        return jsonify({'error': 'Tous les champs sont requis'}), 400
    if password != password_confirm:
        return jsonify({'error': 'Les mots de passe ne correspondent pas'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Le mot de passe doit contenir au moins 6 caractères'}), 400
    
    password_hash = generate_password_hash(password)
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (pseudo, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                  (pseudo, email, password_hash, str(datetime.now())))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Inscription réussie. Conservez bien vos informations de connexion (Email/pseudo et mot de passe). Si vous les avez oubliés, recréez un compte.'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email ou pseudo déjà utilisé'}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    identifier = data.get('identifier')
    password = data.get('password')
    if not identifier or not password:
        return jsonify({'error': 'Identifiant (email ou pseudo) et mot de passe requis'}), 400
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, pseudo, email, password_hash FROM users WHERE email = ? OR pseudo = ?", (identifier, identifier))
    user = c.fetchone()
    conn.close()
    if user and check_password_hash(user[3], password):
        session['user_id'] = user[0]
        session['user_pseudo'] = user[1]
        return jsonify({'message': 'Connexion réussie', 'pseudo': user[1]}), 200
    return jsonify({'error': 'Identifiant ou mot de passe incorrect'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Déconnexion réussie'}), 200

@app.route('/api/me', methods=['GET'])
def me():
    if 'user_id' in session:
        return jsonify({'logged_in': True, 'pseudo': session['user_pseudo']}), 200
    return jsonify({'logged_in': False}), 200

# ================= ROUTES PROTÉGÉES =================
@app.route('/generer_jour_expertise', methods=['POST'])
@login_required
def generer_jour_expertise_route():
    try:
        data = request.get_json()
        domaine = data.get('domaine')
        jour = data.get('jour')
        if not domaine or not jour:
            return jsonify({'error': 'Domaine et jour requis'}), 400
        contenu = generer_jour_expertise(domaine, int(jour))
        return jsonify({'contenu': contenu})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generer_chapitre', methods=['POST'])
@login_required
def generer_chapitre_route():
    try:
        data = request.get_json()
        texte = data.get('texte')
        num = data.get('num')
        if not texte or not num:
            return jsonify({'error': 'Texte et numéro requis'}), 400
        prompt = PROMPT_CHAPITRE_JOUR.format(texte_chapitre=texte, jour_num=num)
        contenu = call_deepseek(prompt, max_tokens=3000)
        contenu = clean_markdown(contenu)
        contenu = remove_markdown_chars(contenu)
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

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
