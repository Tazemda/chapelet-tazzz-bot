import os
import re
import sqlite3
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, render_template, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tazbot-secret-key")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")  # Pour l'envoi d'email

# ================= BASE DE DONNÉES UTILISATEURS =================
def init_users_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  pseudo TEXT UNIQUE NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  confirmed INTEGER DEFAULT 0,
                  confirmation_token TEXT UNIQUE,
                  token_expiry TEXT,
                  created_at TEXT)''')
    conn.commit()
    conn.close()
init_users_db()

def send_confirmation_email(email, pseudo, token):
    confirm_url = url_for('confirm_email', token=token, _external=True)
    if not RESEND_API_KEY:
        # Mode développement : afficher le lien dans la console
        print(f"\n=== LIEN DE CONFIRMATION (mode dev) ===\n{confirm_url}\n====================================\n")
        return True
    try:
        html = f"""
        <h2>Bienvenue {pseudo} !</h2>
        <p>Merci de vous être inscrit sur Chapelet Tazzz Bot.</p>
        <p>Veuillez confirmer votre adresse email en cliquant sur le lien ci-dessous :</p>
        <a href="{confirm_url}">Confirmer mon inscription</a>
        <p>Ce lien expirera dans 24 heures.</p>
        """
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
            json={
                "from": "onboarding@resend.dev",
                "to": email,
                "subject": "Confirmation d'inscription - Chapelet Tazzz Bot",
                "html": html
            }
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"Erreur envoi email: {e}")
        return False

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentification requise'}), 401
        return f(*args, **kwargs)
    return decorated

# ================= FONCTIONS IA (inchangées) =================
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
    except requests.exceptions.Timeout:
        raise Exception("L'API DeepSeek a mis trop de temps à répondre. Réessayez.")
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

# ================= ROUTES D'AUTH =================
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
    token = secrets.token_urlsafe(32)
    token_expiry = (datetime.now() + timedelta(hours=24)).isoformat()
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (pseudo, email, password_hash, confirmation_token, token_expiry, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                  (pseudo, email, password_hash, token, token_expiry, str(datetime.now())))
        conn.commit()
        conn.close()
        if send_confirmation_email(email, pseudo, token):
            return jsonify({'message': 'Inscription réussie. Vérifiez vos emails pour confirmer.'}), 201
        else:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE email = ?", (email,))
            conn.commit()
            conn.close()
            return jsonify({'error': 'Erreur envoi email. Réessayez.'}), 500
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email ou pseudo déjà utilisé'}), 400

@app.route('/confirm/<token>')
def confirm_email(token):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, email, token_expiry FROM users WHERE confirmation_token = ? AND confirmed = 0", (token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return "Lien invalide ou déjà utilisé.", 400
    if datetime.now() > datetime.fromisoformat(user[2]):
        conn.close()
        return "Lien expiré. Veuillez vous réinscrire.", 400
    c.execute("UPDATE users SET confirmed = 1, confirmation_token = NULL WHERE id = ?", (user[0],))
    conn.commit()
    conn.close()
    return "Votre inscription est validée ! Vous pouvez vous connecter.", 200

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'Email et mot de passe requis'}), 400
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, pseudo, email, password_hash, confirmed FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()
    if user and check_password_hash(user[3], password):
        if user[4] != 1:
            return jsonify({'error': 'Confirmez votre email avant de vous connecter.'}), 401
        session['user_id'] = user[0]
        session['user_pseudo'] = user[1]
        return jsonify({'message': 'Connexion réussie', 'pseudo': user[1]}), 200
    return jsonify({'error': 'Email ou mot de passe incorrect'}), 401

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
