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

def call_deepseek(prompt, max_tokens=3500, timeout=240, retries=2):
    if not DEEPSEEK_API_KEY:
        raise Exception("Clé API DeepSeek manquante")
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
            if attempt == retries:
                raise Exception(f"Timeout après {retries+1} tentatives")
            continue
        except Exception as e:
            if attempt == retries:
                raise e
            continue
    raise Exception("Échec inattendu")

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

# ================= EXPERTISE =================
PROMPT_JOUR = """
Tu es un expert pédagogique. Domaine : "{domaine}".

Génère le contenu du **Jour {jour_num}** (objectif : {titre_objectif}) pour un chapelet d’apprentissage.

**RÈGLES STRICTES** :
- Commence par écrire le titre : `## **JOUR {jour_num} – [TITRE PERTINENT EN MAJUSCULES, ADAPTÉ AU DOMAINE]`
- Ensuite, EXACTEMENT 5 DIZAINES (DIZAINE 1 à 5). Pour chaque DIZAINE, utilise ce format exact :

**DIZAINE X – Concept : [nom du concept]**

**Méditation synthèse générale** (gros grain) : (3 à 5 phrases denses, avec définition, rôle, application concrète – comme une mini-fiche de cours)

**répète ceci 3 x (pas de graines)** : (une seule phrase : une question centrale pertinente conduisant à la compréhension du sujet et montrant le problème clé que cela permet de résoudre)

**répète ceci 10 x (les 10 petites graines)** : (4 à 6 phrases synthétiques, mémorisables, qui résument le concept)

**répète ceci 3 x:** "Le concept [nom du concept] est consolidé."

Ne dépasse pas 3500 tokens au total. Soigne la qualité et l’adaptation au domaine. Utilise exactement les libellés ci-dessus.
"""

def generer_jour_expertise(domaine, jour_num, tentative=1):
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
        raw = call_deepseek(prompt, max_tokens=3500, timeout=240, retries=2)
        contenu = clean_markdown(raw)
        if not re.search(r'##\s*\*\*JOUR\s+\d+', contenu, re.IGNORECASE):
            contenu = f"## **JOUR {jour_num} – {titre_objectif.upper()}**\n\n{contenu}"
        # Vérifier qu'il y a bien 5 DIZAINE
        if contenu.count("**DIZAINE") < 5:
            raise Exception("Nombre de dizaines insuffisant")
        return contenu
    except Exception as e:
        if tentative < 3:
            # Réessayer avec un token maximum plus grand
            return generer_jour_expertise(domaine, jour_num, tentative+1)
        else:
            return f"❌ **Erreur de génération pour le jour {jour_num}** : {str(e)}\n\nVeuillez réessayer plus tard."

# ================= MODE PERSONNEL (similaire mais avec les mêmes intitulés ? non, l'utilisateur n'a pas demandé) =================
# On garde une version simple mais fonctionnelle (pas de changement demandé)
def generer_personnel(defauts):
    notre_pere = "Mon cerveau, par sa plasticité infinie, se réorganise chaque jour."
    resultats = []
    for i, d in enumerate(defauts, 1):
        prompt = f"""
Génère un **Mystère {i}** pour le défaut : "{d}".
Structure :
**Mystère {i} – {d}**
**Méditation synthèse générale** (gros grain) : (rappel d’un échec + visualisation positive, 2-3 phrases)
**répète ceci 3 x (pas de graines)** : "{notre_pere}"
**répète ceci 10 x (les 10 petites graines)** : (une phrase courte positive qui corrige ce défaut)
**répète ceci 3 x:** "Je remercie Dieu et l'univers pour cette transformation."
"""
        try:
            raw = call_deepseek(prompt, max_tokens=800, timeout=120)
            resultats.append(clean_markdown(raw))
        except Exception as e:
            resultats.append(f"❌ **Erreur pour le défaut {i}** : {str(e)}")
    return "\n\n".join(resultats)

# ================= ROUTES =================
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
