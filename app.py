import os
import json
import re
import requests
import traceback
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tazbot-secret-key")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

def call_deepseek(prompt, system_message="Tu es l'assistant Tazzz Bot."):
    if not DEEPSEEK_API_KEY:
        raise Exception("Clé API DeepSeek manquante")
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 3000,
        "timeout": 45
    }
    try:
        resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
    except requests.exceptions.Timeout:
        raise Exception("Timeout: DeepSeek ne répond pas après 60 secondes.")
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"API DeepSeek error {resp.status_code}: {resp.text}")

def clean_markdown(text):
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = text.replace('`', '')
    return text.strip()

def generate_mock_expertise(domaine):
    """Génère un chapelet d'expertise factice sans appeler l'API."""
    return f"""
**⚠️ MODE DÉGRADÉ : L'API DeepSeek n'a pas répondu (vérifiez votre clé, solde, ou logs). Voici un exemple de chapelet pour « {domaine} ».**

**Rappel** : outil de mémorisation active par répétition rythmée.

**Point d’entrée du problème** : Comment maîtriser {domaine} efficacement ?

**Règle d’or** : Pratiquer chaque jour une dizaine.

**DIZAINE 1 – Concept : Fondamentaux**
- **Méditation** : Définitions et principes de base de {domaine}.
- **Notre Père (3x)** : Quelle est la première notion à retenir ?
- **Je vous salue Marie (10x)** : (paragraphe) Les concepts clés sont A, B, C ; leur compréhension permet d’avancer.
- **Gloire au Père (3x)** : Le concept « fondamentaux » est consolidé.

**DIZAINE 2 – Concept : Méthodologie**
- **Méditation** : Étapes et outils pratiques.
- **Notre Père (3x)** : Comment appliquer la méthode en situation réelle ?
- **Je vous salue Marie (10x)** : (paragraphe) La méthode se décompose en trois phases : analyse, action, contrôle.
- **Gloire au Père (3x)** : Le concept « méthodologie » est consolidé.

**DIZAINE 3 – Concept : Cas d’usage**
- **Méditation** : Exemples concrets dans {domaine}.
- **Notre Père (3x)** : Quelles sont les erreurs fréquentes à éviter ?
- **Je vous salue Marie (10x)** : (paragraphe) Les cas typiques sont X, Y, Z ; leur résolution passe par la grille d’analyse.
- **Gloire au Père (3x)** : Le concept « cas d’usage » est consolidé.

**DIZAINE 4 – Concept : Outils d’audit**
- **Méditation** : Instruments de contrôle et indicateurs.
- **Notre Père (3x)** : Comment mesurer la performance ?
- **Je vous salue Marie (10x)** : (paragraphe) Les outils incluent les checklists, les entretiens, l’observation directe.
- **Gloire au Père (3x)** : Le concept « outils » est consolidé.

**DIZAINE 5 – Concept : Gestion des risques**
- **Méditation** : Anticipation et correction des écarts.
- **Notre Père (3x)** : Quels sont les signaux d’alerte ?
- **Je vous salue Marie (10x)** : (paragraphe) La gestion des risques repose sur l’analyse des non-conformités et le plan d’action.
- **Gloire au Père (3x)** : Le concept « gestion des risques » est consolidé.

Chapelet Tazzz Bot – Basé sur la plasticité cérébrale et la répétition rythmée.
Copyright Dr Tazemda
"""

# ------------------ PROMPT EXPERTISE (réduit à un jour) ------------------
PROMPT_EXPERTISE = """
Génère un CHAPELET TAZZZ BOT – MODE EXPERTISE (7 jours) pour le domaine : {domaine}. Commence par le Jour 1 seulement (5 dizaines). Utilise la structure détaillée comme dans les exemples précédents.
"""

# ... (les autres prompts restent identiques à la version précédente) ...

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    mode = data.get('mode')
    if mode == 'expertise':
        domaine = data.get('domaine')
        if not domaine:
            return jsonify({'error': 'Domaine requis'}), 400
        try:
            prompt = PROMPT_EXPERTISE.format(domaine=domaine)
            raw = call_deepseek(prompt)
            chapelet = clean_markdown(raw)
        except Exception as e:
            print("ERREUR API, fallback mock:", e)
            chapelet = generate_mock_expertise(domaine)
            return jsonify({'chapelet': chapelet, 'warning': f'API indisponible : {str(e)}. Utilisation d’un exemple.'})
        return jsonify({'chapelet': chapelet})

    # ... les autres modes (personnel, consultation) conservent call_deepseek sans fallback
