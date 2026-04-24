import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tazbot-secret-key")

# ------------------ BASE DE DONNÉES ------------------
def init_db():
    conn = sqlite3.connect('tazbot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS chapelets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT,
                  mode TEXT,
                  input TEXT,
                  contenu TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS feedback
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT,
                  note INTEGER,
                  commentaire TEXT)''')
    conn.commit()
    conn.close()

init_db()

def sauvegarder_chapelet(mode, input_utilisateur, contenu):
    conn = sqlite3.connect('tazbot.db')
    c = conn.cursor()
    c.execute("INSERT INTO chapelets (date, mode, input, contenu) VALUES (?, ?, ?, ?)",
              (str(datetime.now()), mode, input_utilisateur, contenu))
    conn.commit()
    conn.close()

# ------------------ GÉNÉRATION CHAPELET EXPERTISE (mock 7 jours) ------------------
def generate_mock_expertise(domaine):
    # (même code que précédemment, trop long à répéter, mais vous pouvez garder votre version)
    # Pour simplifier, je donne une version courte illustrative. Utilisez votre vrai code.
    return f"""
--- Jour 1 – Découverte des bases du {domaine} ---
[Contenu simulé – remplacez par votre génération réaliste]
...
Chapelet Tazzz Bot – Basé sur la plasticité cérébrale et la répétition rythmée.
Copyright Dr Tazemda
"""

def generate_mock_personnel(defauts):
    mantra = "Je me lève tôt, je termine ce que je commence, je sors chaque jour, je structure ma vie, j'attire un travail stable et prospère."
    texte = f"""
**CHAPELET TAZZZ BOT – MODE DÉVELOPPEMENT PERSONNEL (21/66 jours)**

> Munissez-vous d'un chapelet pour égrener chaque grain...

### DÉBUT
...
### 5 MYSTÈRES
"""
    for i, d in enumerate(defauts, 1):
        texte += f"**Mystère {i} – {d}**\n...\n"
    texte += "### FIN\nChapelet Tazzz Bot – ...\nCopyright Dr Tazemda"
    return texte

# ------------------ ROUTES ------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    mode = data.get('mode')
    if mode == 'expertise':
        domaine = data.get('domaine')
        if not domaine:
            return jsonify({'error': 'Domaine requis'}), 400
        chapelet = generate_mock_expertise(domaine)
        sauvegarder_chapelet('expertise', domaine, chapelet)
        return jsonify({'chapelet': chapelet})
    elif mode == 'personnel':
        defauts = data.get('defauts')
        if not defauts or len(defauts) != 5:
            return jsonify({'error': '5 défauts requis'}), 400
        chapelet = generate_mock_personnel(defauts)
        sauvegarder_chapelet('personnel', str(defauts), chapelet)
        return jsonify({'chapelet': chapelet})
    elif mode == 'consultation':
        message = data.get('message')
        if not message:
            return jsonify({'error': 'Message requis'}), 400
        # simple classification
        if any(w in message.lower() for w in ['maîtriser', 'apprendre', 'domaine', 'entretien']):
            domaine = message[:150]
            chapelet = generate_mock_expertise(domaine)
            sauvegarder_chapelet('consultation_expertise', message, chapelet)
            return jsonify({'chapelet': chapelet, 'message_info': '🔍 Type détecté : EXPERTISE'})
        else:
            defauts = ["Je manque de discipline"] * 5
            chapelet = generate_mock_personnel(defauts)
            sauvegarder_chapelet('consultation_personnel', message, chapelet)
            return jsonify({'chapelet': chapelet, 'message_info': '🔍 Type détecté : PERSONNEL'})
    return jsonify({'error': 'Mode invalide'}), 400

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
