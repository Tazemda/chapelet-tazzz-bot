import os
import re
import sqlite3
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, render_template, session, url_for, redirect
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tazbot-secret-key")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")

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
                  reset_token TEXT UNIQUE,
                  reset_token_expiry TEXT,
                  created_at TEXT)''')
    conn.commit()
    conn.close()
init_users_db()

def send_email(to, subject, html_content):
    if not RESEND_API_KEY:
        print(f"\n=== EMAIL (non envoyé, clé manquante) ===\nÀ: {to}\nSujet: {subject}\n{html_content}\n================================\n")
        return True
    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
            json={
                "from": "onboarding@resend.dev",
                "to": to,
                "subject": subject,
                "html": html_content
            },
            timeout=10
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"Erreur envoi email: {e}")
        return False

def send_confirmation_email(email, pseudo, token):
    confirm_url = url_for('confirm_email', token=token, _external=True)
    html = f"<h2>Bienvenue {pseudo} !</h2><p>Cliquez pour confirmer : <a href='{confirm_url}'>Confirmer</a></p><p>Lien valable 24h.</p>"
    return send_email(email, "Confirmation d'inscription - Chapelet Tazzz Bot", html)

def send_reset_email(email, token):
    reset_url = url_for('reset_password_page', token=token, _external=True)
    html = f"<h2>Réinitialisation mot de passe</h2><p>Cliquez pour réinitialiser : <a href='{reset_url}'>Réinitialiser</a></p><p>Lien valable 1 heure.</p>"
    return send_email(email, "Réinitialisation mot de passe - Chapelet Tazzz Bot", html)

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
PROMPT_JOUR = """... (identique à avant) ..."""
PROMPT_CHAPITRE_JOUR = """... (identique) ..."""

def generer_jour_expertise(domaine, jour_num):
    # ... (identique à avant) ...
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

# ================= MOT DE PASSE OUBLIÉ =================
@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({'error': 'Email requis'}), 400
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email = ? AND confirmed = 1", (email,))
    user = c.fetchone()
    if not user:
        conn.close()
        # Pour éviter de révéler l'existence d'un compte, on renvoie un message générique
        return jsonify({'message': 'Si cet email existe et est confirmé, vous recevrez un lien de réinitialisation.'}), 200
    
    reset_token = secrets.token_urlsafe(32)
    reset_expiry = (datetime.now() + timedelta(hours=1)).isoformat()
    c.execute("UPDATE users SET reset_token = ?, reset_token_expiry = ? WHERE id = ?", (reset_token, reset_expiry, user[0]))
    conn.commit()
    conn.close()
    
    if send_reset_email(email, reset_token):
        return jsonify({'message': 'Un email de réinitialisation vous a été envoyé.'}), 200
    else:
        return jsonify({'error': "Erreur lors de l'envoi de l'email. Réessayez."}), 500

@app.route('/reset-password/<token>', methods=['GET'])
def reset_password_page(token):
    # Page HTML simple pour saisir le nouveau mot de passe
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Réinitialisation mot de passe</title><style>body{{font-family:sans-serif;background:#1a2a36;color:#fff;padding:20px;}}.container{{max-width:400px;margin:0 auto;background:rgba(0,0,0,0.5);padding:20px;border-radius:16px;}}input{{width:100%;padding:10px;margin:10px 0;border-radius:8px;border:none;}}button{{background:#e67e22;border:none;padding:10px;border-radius:8px;cursor:pointer;}}button:hover{{background:#d35400;}}</style></head>
    <body>
    <div class="container">
        <h2>Réinitialisation mot de passe</h2>
        <form id="resetForm">
            <input type="password" id="password" placeholder="Nouveau mot de passe (min 6 car.)" required>
            <input type="password" id="confirm" placeholder="Confirmer" required>
            <button type="submit">Valider</button>
        </form>
        <div id="message"></div>
    </div>
    <script>
        document.getElementById('resetForm').onsubmit = async (e) => {{
            e.preventDefault();
            const pwd = document.getElementById('password').value;
            const confirm = document.getElementById('confirm').value;
            const token = '{token}';
            if (pwd !== confirm) {{ alert('Mots de passe différents'); return; }}
            if (pwd.length < 6) {{ alert('Mot de passe trop court'); return; }}
            const res = await fetch('/api/reset-password', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ token, password: pwd, password_confirm: confirm }})
            }});
            const data = await res.json();
            document.getElementById('message').innerHTML = data.message || data.error;
            if (res.ok) setTimeout(() => window.location.href = '/', 3000);
        }};
    </script>
    </body>
    </html>
    """

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token')
    password = data.get('password')
    password_confirm = data.get('password_confirm')
    
    if not token or not password or not password_confirm:
        return jsonify({'error': 'Données incomplètes'}), 400
    if password != password_confirm:
        return jsonify({'error': 'Les mots de passe ne correspondent pas'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Mot de passe trop court'}), 400
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, reset_token_expiry FROM users WHERE reset_token = ?", (token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'Lien invalide'}), 400
    if datetime.now() > datetime.fromisoformat(user[1]):
        conn.close()
        return jsonify({'error': 'Lien expiré. Refaites une demande.'}), 400
    
    password_hash = generate_password_hash(password)
    c.execute("UPDATE users SET password_hash = ?, reset_token = NULL, reset_token_expiry = NULL WHERE id = ?", (password_hash, user[0]))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Mot de passe modifié avec succès. Vous pouvez vous connecter.'}), 200

# ================= ROUTES PROTÉGÉES (inchangées) =================
@app.route('/generer_jour_expertise', methods=['POST'])
@login_required
def generer_jour_expertise_route():
    # ... (identique à avant) ...
    pass

@app.route('/generer_chapitre', methods=['POST'])
@login_required
def generer_chapitre_route():
    # ... (identique) ...
    pass

@app.route('/feedback', methods=['POST'])
def feedback():
    # ... identique ...
    pass

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
