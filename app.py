import os
import re
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

def call_deepseek(prompt):
    if not DEEPSEEK_API_KEY:
        raise Exception("Clé API manquante")
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],  # Pas de system message
        "temperature": 0.7,
        "max_tokens": 3000
    }
    resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=90)
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"API error {resp.status_code}: {resp.text[:200]}")

def generate_jour(domaine, jour_num):
    # Objectifs des jours (génériques)
    objectifs = [
        "Découvrir les bases fondamentales",
        "Approfondir les pratiques courantes",
        "Gérer les cas complexes et exceptions",
        "Mettre en place des indicateurs de contrôle",
        "Anticiper et gérer les risques",
        "Faire la synthèse des liens entre concepts",
        "S'auto-évaluer et se perfectionner"
    ]
    prompt = f"""
Génère le contenu du **Jour {jour_num}** d'un chapelet d'apprentissage sur le domaine : "{domaine}".
Objectif de ce jour : {objectifs[jour_num-1]}.

Le chapelet doit aider l'utilisateur à maîtriser ce domaine. Pour ce jour, invente **5 concepts** (DIZAINE 1 à 5) et pour chaque concept, écris :

- **1) Méditation (grande fiche)** : un paragraphe dense (définitions, exemples, points clés).
- **2) Notre Père** : une question problématique que l'utilisateur doit se poser (à répéter 3 fois).
- **3) Je vous salue Marie** : un paragraphe synthétique résumant le concept (à répéter 10 fois).
- **4) Gloire au Père** : une phrase de consolidation du concept.

Format à respecter :
**DIZAINE 1 – Concept : [nom]**
**1) Méditation** ...  
**2) Notre Père** ...  
**3) Je vous salue Marie** ...  
**4) Gloire au Père** ...

Fais exactement 5 dizaines. Adapte tout au domaine "{domaine}". Ne parle pas d'autre sujet.
Commence directement par "**DIZAINE 1**". N'ajoute pas de titre global avant.
"""
    raw = call_deepseek(prompt)
    # On nettoie les éventuels marqueurs markdown
    raw = re.sub(r'```[\s\S]*?```', '', raw).replace('`', '')
    return f"--- Jour {jour_num} – {objectifs[jour_num-1]} ---\n\n" + raw.strip()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generer_jour', methods=['POST'])
def generer_jour_route():
    data = request.get_json()
    domaine = data.get('domaine')
    jour = data.get('jour')
    if not domaine or not jour:
        return jsonify({'error': 'Domaine et jour requis'}), 400
    try:
        contenu = generate_jour(domaine, jour)
        return jsonify({'contenu': contenu})
    except Exception as e:
        return jsonify({'contenu': f"--- Jour {jour} (erreur) ---\n{e}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
