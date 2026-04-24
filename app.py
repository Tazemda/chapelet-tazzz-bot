import os
import sqlite3
import re
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tazbot-secret-key")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# ------------------ BASE SQLITE ------------------
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

# ------------------ APPEL API ------------------
def call_deepseek(prompt, system_message="Tu es un expert pédagogique."):
    if not DEEPSEEK_API_KEY:
        raise Exception("Clé API DeepSeek manquante")
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2500
    }
    resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=90)
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"API error {resp.status_code}: {resp.text[:200]}")

def clean_markdown(text):
    text = re.sub(r'```[\s\S]*?```', '', text)
    return text.replace('`', '').strip()

# ------------------ PROMPT POUR UN JOUR (1 à 7) ------------------
PROMPT_JOUR = """
Tu es un expert en pédagogie. Génère le **Jour {jour_num} – {titre}** d’un chapelet d’apprentissage sur le domaine : « {domaine} ».

Le chapelet complet comporte 7 jours. Voici le plan des jours :
Jour 1 – Découverte des bases
Jour 2 – Approfondissement opérationnel
Jour 3 – Cas complexes et exceptions
Jour 4 – Contrôle qualité et indicateurs
Jour 5 – Gestion des risques et plan d'action
Jour 6 – Synthèse et liens entre concepts
Jour 7 – Auto‑évaluation et perfectionnement

Pour le jour demandé, tu dois produire exactement le format suivant (5 dizaines) :

--- Jour {jour_num} – {titre} ---

**DIZAINE 1 – Concept : (nom du concept)**

**1) Méditation (grande fiche)**  
*Instruction : Tenez le gros grain. Lisez ce paragraphe comme une fiche de cours.*  
(Paragraphe dense : définition, exemples, points clés. Adapté au domaine.)

**2) Notre Père**  
*Récitez cette question 3 fois.*  
« (Question problématique sur le concept) »

**3) Je vous salue Marie**  
*Répétez ce paragraphe 10 fois (5 lectures, 5 sans regarder).*  
(Paragraphe synthétique de plusieurs phrases résumant le concept.)

**4) Gloire au Père**  
*Récitez cette phrase 3 fois.*  
« Le concept “(nom du concept)” est connu et consolidé. »

(Recommence pour DIZAINE 2, 3, 4, 5 avec des concepts différents et pertinents pour le jour.)

Termine par : (rien de plus, pas de copyright ici).

Soigne la qualité : les méditations doivent être instructives, les Ave Maria denses mais clairs, les questions pertinentes.
"""

def generer_jour(domaine, jour_num):
    titres = [
        "Découverte des bases",
        "Approfondissement opérationnel",
        "Cas complexes et exceptions",
        "Contrôle qualité et indicateurs",
        "Gestion des risques et plan d'action",
        "Synthèse et liens entre concepts",
        "Auto‑évaluation et perfectionnement"
    ]
    titre = titres[jour_num-1]
    prompt = PROMPT_JOUR.format(jour_num=jour_num, titre=titre, domaine=domaine)
    raw = call_deepseek(prompt)
    return clean_markdown(raw)

# ------------------ FALLBACK (si API échoue) ------------------
def fallback_jour(domaine, jour_num):
    return f"--- Jour {jour_num} (mode dégradé) ---\nImpossible de générer le contenu via DeepSeek. Vérifiez votre clé API ou votre crédit."

# ------------------ ROUTES ------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_jour', methods=['POST'])
def generate_jour():
    data = request.get_json()
    domaine = data.get('domaine')
    jour = data.get('jour')
    if not domaine or not jour:
        return jsonify({'error': 'Domaine et jour requis'}), 400
    try:
        contenu = generer_jour(domaine, jour)
        # Sauvegarde de l'intégralité (optionnel) - on pourrait sauvegarder jour par jour
        # mais on peut aussi sauvegarder seulement à la fin. Pour simplifier, on ne sauvegarde pas ici.
        return jsonify({'contenu': contenu})
    except Exception as e:
        print("Erreur génération jour:", e)
        contenu = fallback_jour(domaine, jour)
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
