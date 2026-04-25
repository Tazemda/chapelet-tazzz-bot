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

def call_deepseek(prompt, max_tokens=4000):
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
            raise Exception(f"API error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        raise Exception(f"Erreur API: {str(e)}")

def clean_markdown(text):
    text = re.sub(r'```[\s\S]*?```', '', text)
    return text.replace('`', '').strip()

def verifier_et_completer_jour(contenu, domaine, jour_num):
    """Garantit que le contenu contient 5 dizaines complètes."""
    # Vérifier le titre
    if not re.search(r'##\s*\*\*JOUR\s+\d+', contenu, re.IGNORECASE):
        objectifs = [
            "Découverte des bases fondamentales",
            "Approfondissement des pratiques clés",
            "Cas complexes et exceptions",
            "Contrôle qualité et indicateurs",
            "Gestion des risques et plan d'action",
            "Synthèse et liens entre concepts",
            "Auto‑évaluation et perfectionnement"
        ]
        contenu = f"## **JOUR {jour_num} – {objectifs[jour_num-1].upper()}**\n\n{contenu}"
    
    # Compter les dizaines
    matches = list(re.finditer(r'\*\*DIZAINE (\d+) – Concept', contenu, re.IGNORECASE))
    found = [int(m.group(1)) for m in matches]
    needed = set(range(1, 6))
    missing = needed - set(found)
    
    if not missing:
        return contenu
    
    # Compléter les dizaines manquantes à la fin
    for m in sorted(missing):
        contenu += f"""

**DIZAINE {m} – Concept : (concept à définir pour {domaine})**
**1) Méditation** : (développez ce concept en lien avec {domaine})
**2) Notre Père** : (question problématique sur ce concept)
**3) Je vous salue Marie** : (paragraphe synthétique de plusieurs phrases)
**4) Gloire au Père** : "Le concept est consolidé.""""
    
    return contenu

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

# ================= PROMPT OPTIMISÉ (ÉVITE LA TRONCATURE) =================
PROMPT_JOUR = """
Tu es un expert pédagogique. Domaine : "{domaine}".

Génère le contenu complet du **Jour {jour_num}** (objectif : {titre_objectif}).

**IMPORTANT :** Tu dois produire un texte **complet, non tronqué**. La longueur totale ne doit pas dépasser 3000 tokens (soit environ 2000 mots). Sois exhaustif mais concis. Évite les répétitions.

Commence par le titre :  
## **JOUR {jour_num} – [TITRE PERTINENT EN MAJUSCULES, ADAPTÉ AU DOMAINE]**

Puis rédige **5 DIZAINES** exactement. Chaque dizaine doit suivre ce modèle :

**DIZAINE 1 – Concept : [nom du concept]**
**1) Méditation** : (paragraphe dense avec définitions, exemples, points clés – 3 à 5 phrases)
**2) Notre Père** : (une question problématique, une phrase)
**3) Je vous salue Marie** : (paragraphe synthétique de 3 à 4 phrases, à mémoriser)
**4) Gloire au Père** : "Le concept "[nom]" est consolidé."

Répète pour **DIZAINE 2**, **3**, **4**, **5**.

Contenu directement utilisable pour un apprentissage autonome. Ne mets rien avant le titre.
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
        raw = call_deepseek(prompt, max_tokens=4000)  # Augmenté pour sécurité
        contenu = clean_markdown(raw)
        contenu = verifier_et_completer_jour(contenu, domaine, jour_num)
        return contenu
    except Exception as e:
        print(f"Erreur API jour {jour_num}: {e}")
        fallback = f"""## **JOUR {jour_num} – {titre_objectif.upper()}** (mode dégradé)

**DIZAINE 1 – Introduction à {domaine}**
**1) Méditation** : (contenu temporaire – veuillez relancer la génération)
**2) Notre Père** : ?
**3) Je vous salue Marie** : ...
**4) Gloire au Père** : consolidé.
"""
        for i in range(2, 6):
            fallback += f"""

**DIZAINE {i} – Concept supplémentaire**
**1) Méditation** : (à compléter)
**2) Notre Père** : ?
**3) Je vous salue Marie** : ...
**4) Gloire au Père** : consolidé."""
        return fallback

# ================= DÉVELOPPEMENT PERSONNEL (simplifié) =================
def generer_personnel(defauts):
    notre_pere = "Mon cerveau, par sa plasticité infinie, se réorganise chaque jour."
    resultats = []
    for i, d in enumerate(defauts, 1):
        prompt = f"Mystère {i} – {d}\n**Méditation** : souvenir d'un échec puis visualisation positive.\n**Notre Père** : {notre_pere} (3 fois)\n**Je vous salue Marie** : phrase courte positive (10 fois)\n**Gloire au Père** : Merci (3 fois)"
        try:
            raw = call_deepseek(prompt, max_tokens=500)
            resultats.append(clean_markdown(raw))
        except:
            resultats.append(f"**Mystère {i} – {d}** (version de secours)")
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
