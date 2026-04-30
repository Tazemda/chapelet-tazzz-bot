import os
import re
import sqlite3
import secrets
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tazbot-secret-key")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")  # Clé API Resend (gratuite)

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
    if not RESEND_API_KEY:
        print(f"Lien de confirmation (mode dev) : {url_for('confirm_email', token=token, _external=True)}")
        return True
    try:
        confirm_url = url_for('confirm_email', token=token, _external=True)
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
    except:
        return False

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

# ================= PROMPTS (inchangés) =================
PROMPT_JOUR = """... (identique à avant) ..."""
PROMPT_CHAPITRE_JOUR = """... (identique) ..."""

def generer_jour_expertise(domaine, jour_num):
    # ... identique ...
    pass

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
        return jsonify({'error': 'Mot de passe trop court (min 6 caractères)'}), 400
    
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
        return "Lien expiré. Veuillez réinscrire.", 400
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
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentification requise'}), 401
        return f(*args, **kwargs)
    return decorated

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
    # ... inchangé ...
    pass

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
