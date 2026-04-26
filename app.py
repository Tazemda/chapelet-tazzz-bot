import os
import re
import sqlite3
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tazbot-secret-key")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# ---------- Appel API avec réessais intelligents ----------
def call_deepseek(prompt, max_tokens=3500, timeout=180, retries=2):
    if not DEEPSEEK_API_KEY:
        raise Exception("❌ Clé API DeepSeek manquante")
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
                time.sleep(2)
                continue
            raise Exception("⏱️ Timeout – DeepSeek ne répond pas. Réessayez plus tard.")
        except Exception as e:
            if attempt < retries:
                time.sleep(2)
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

# ---------- PROMPT avec les libellés exacts ----------
PROMPT_JOUR = """
Tu es un expert pédagogique. Domaine : "{domaine}".

Génère le contenu complet du **Jour {jour_num}** sur 7 jours.  
L'objectif général du jour {jour_num} est : {titre_objectif}.

Commence par écrire le **titre du jour** sous la forme (obligatoire) :
## **JOUR {jour_num} – [TITRE PERTINENT EN MAJUSCULES, ADAPTÉ AU DOMAINE]**

Puis, rédige exactement **5 DIZAINES** selon le modèle ci‑dessous.  
Adapte chaque concept, exemple et question au domaine "{domaine}".

Chaque dizaine doit suivre ce format exact (ne mets pas les mentions "répète ceci" dans le texte – ce sont des instructions pour l'utilisateur) :

**DIZAINE X – Concept : [nom du concept]**

**Méditation synthèse générale (gros grain)**
(paragraphe dense avec définitions, exemples concrets, points clés)

**Notre Père** (répète ceci 3 x – pas de graines)
(une seule phrase : une question centrale pertinente)

**Je vous salue Marie** (répète ceci 10 x – les 10 petites graines)
(un paragraphe de 5 à 8 phrases, synthétique et mémorisable)

**Gloire au Père** (répète ceci 3 x)
(une phrase courte : "Le concept [nom] est consolidé.")

Répète pour DIZAINE 2 à 5.
Soigne la qualité et l'exhaustivité. Contenu directement utilisable.
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

    # Premier appel avec tokens modérés
    raw = call_deepseek(prompt, max_tokens=3500, timeout=180, retries=2)
    contenu = clean_markdown(raw)

    # Vérification du nombre de dizaines (5 attendues)
    nb_dizaines = contenu.count("**DIZAINE")
    if nb_dizaines < 5:
        # Relance avec plus de tokens
        raw = call_deepseek(prompt, max_tokens=4500, timeout=240, retries=1)
        contenu = clean_markdown(raw)
        nb_dizaines = contenu.count("**DIZAINE")
        if nb_dizaines < 5:
            # Fallback : on ajoute un message d'erreur mais on conserve ce qui a été généré
            contenu += "\n\n⚠️ **Attention** : Le contenu complet n'a pas pu être généré (seulement {} dizaines sur 5). Relancez le jour ou vérifiez votre connexion.".format(nb_dizaines)

    # Vérification du titre
    if not re.search(r'##\s*\*\*JOUR\s+\d+', contenu, re.IGNORECASE):
        contenu = f"## **JOUR {jour_num} – {titre_objectif.upper()}**\n\n{contenu}"

    return contenu

# ---------- MODE PERSONNEL (simplifié, mais on peut l'améliorer plus tard) ----------
def generer_personnel(defauts):
    notre_pere = "Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes."
    resultats = []
    for i, d in enumerate(defauts, 1):
        prompt = f"""
Génère un **Mystère {i}** pour le défaut : "{d}".
Format exact :
**Mystère {i} – {d}**
**Méditation synthèse générale (gros grain)** : (2-3 phrases : rappel d'un échec passé puis visualisation positive)
**Notre Père** (répète ceci 3 x) : "{notre_pere}"
**Je vous salue Marie** (répète ceci 10 x) : (une phrase courte positive adaptée à ce défaut)
**Gloire au Père** (répète ceci 3 x) : "Je remercie Dieu et l'univers pour cette transformation."
"""
        try:
            raw = call_deepseek(prompt, max_tokens=800, timeout=120, retries=1)
            resultats.append(clean_markdown(raw))
        except Exception as e:
            resultats.append(f"❌ **Erreur pour le défaut {i}** : {str(e)}")
    return "\n\n".join(resultats)

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
    try:
        contenu = generer_jour_expertise(domaine, int(jour))
        return jsonify({'contenu': contenu})
    except Exception as e:
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
