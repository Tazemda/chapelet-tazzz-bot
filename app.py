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
        raise Exception("Clé API DeepSeek manquante. Ajoute DEEPSEEK_API_KEY dans les variables d'environnement.")
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
        "max_tokens": 2000,  # réduit pour éviter timeout
        "timeout": 45
    }
    try:
        resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
    except requests.exceptions.Timeout:
        raise Exception("Timeout: DeepSeek ne répond pas (plus de 60 secondes).")
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"API DeepSeek error {resp.status_code}: {resp.text}")

def clean_markdown(text):
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = text.replace('`', '')
    return text.strip()

def extract_json(text):
    text = text.strip()
    start = text.find('{')
    if start == -1:
        raise ValueError("Aucune accolade ouvrante")
    brace_count = 0
    end = start
    for i, ch in enumerate(text[start:], start):
        if ch == '{':
            brace_count += 1
        elif ch == '}':
            brace_count -= 1
            if brace_count == 0:
                end = i
                break
    if end == start:
        raise ValueError("JSON non valide")
    return text[start:end+1]

# ------------------ PROMPT EXPERTISE : seulement le Jour 1 pour tester ------------------
PROMPT_EXPERTISE = """
Génère le **Jour 1** d'un CHAPELET TAZZZ BOT – MODE EXPERTISE (7 jours) pour le domaine : {domaine}.

Le chapelet est un outil de mémorisation active par répétition rythmée, basé sur la plasticité cérébrale.
Ne produis que le Jour 1, avec 5 dizaines (concepts fondamentaux). Chaque dizaine suit exactement ce modèle :

**DIZAINE X – Concept : [nom du concept]**

**1. Méditation sur le mystère** :  
(paragraphe dense avec définition, rôle, exemples)

**2. Notre Père (à répéter 3 fois)** :  
(une question problématique ou aide-mémoire)

**3. Je vous salue Marie (à répéter 10 fois)** :  
(plusieurs phrases synthétisant tout le concept – comme dans un cours. Exemple long donné dans les instructions.)

**4. Gloire au Père (à répéter 3 fois)** :  
« Le concept « X » est connu et consolidé. »

Commence par :
**Rappel** : (une phrase)
**Point d’entrée du problème** : (une phrase)
**Règle d’or** : (une phrase)

Termine par :
Chapelet Tazzz Bot – Basé sur la plasticité cérébrale et la répétition rythmée.
Copyright Dr Tazemda
"""

# ------------------ PROMPT PERSONNEL ------------------
PROMPT_PERSONNEL = """
Génère un CHAPELET TAZZZ BOT – MODE DÉVELOPPEMENT PERSONNEL (21 ou 66 jours) pour ces 5 défauts :
{defauts}

Ajoute cette note au début :
> *"Munissez-vous d'un chapelet pour égrener chaque grain correspondant en récitant à voix haute ou mentalement, dans un endroit calme."*

Structure canonique (texte brut) :

### DÉBUT
- Signe de croix : "Au nom de mon engagement, de ma lucidité et de ma persévérance."
- Crucifix : "Je ne subis plus ma vie. Je deviens l'acteur de chaque heure."
- 3 Ave initiaux : (donnés)
- Gloire : "Je rends grâce à la vie pour ce nouveau départ."

### 5 MYSTÈRES (un par défaut)
Pour chaque défaut :
**Mystère X – [nom du défaut]**
**Méditation** : (passé négatif + visualisation positive)
**Notre Père** (à répéter 3 fois) : "Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes. Je choisis ma lucidité."
**10 × Je vous salue Marie** : (une phrase courte unique, résumant la correction des 5 défauts, à répéter 10 fois)
**Gloire au Père** (à répéter 3 fois) : "Je remercie Dieu et l'univers pour ses réalisations dans ma vie et cette transformation profonde."

### FIN
- Salve Regina, Mantra final, Signe de croix final.

Termine par :
Chapelet Tazzz Bot – Basé sur la plasticité cérébrale et la répétition rythmée.
Copyright Dr Tazemda
"""

# ------------------ PROMPT CLASSIFICATION (simplifié) ------------------
PROMPT_CLASSIFY = """
Réponds uniquement par un objet JSON valide, sans texte avant ou après.

Message : "{}"

Règles :
- Expertise (apprendre un domaine technique) → type="expertise", contenu=le domaine
- Personnel (défauts) → type="personnel", contenu=liste de 5 défauts

Exemples :
Message: "Je veux maîtriser l'audit" → {"type": "expertise", "contenu": "Audit"}
Message: "Je me lève tard, paresseux" → {"type": "personnel", "contenu": ["Je me lève tard", "paresseux", "désordonné", "timide", "démotivé"]}
"""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON manquantes'}), 400
        mode = data.get('mode')

        if mode == 'expertise':
            domaine = data.get('domaine')
            if not domaine:
                return jsonify({'error': 'Domaine requis'}), 400
            prompt = PROMPT_EXPERTISE.format(domaine=domaine)
            try:
                raw = call_deepseek(prompt)
                chapelet = clean_markdown(raw)
                return jsonify({'chapelet': chapelet})
            except Exception as e:
                # En cas d'échec, on renvoie un chapelet mock pour ne pas planter l'interface
                mock = f"**ERREUR API : {str(e)}**\n\nGénération d'un chapelet d'exemple pour le domaine '{domaine}'.\n\n"
                mock += "**Rappel** : Cet outil de mémorisation active utilise la répétition.\n"
                mock += "**Point d'entrée** : Comment maîtriser ce domaine rapidement ?\n"
                mock += "**Règle d'or** : Pratique quotidienne.\n\n"
                for i in range(1,6):
                    mock += f"**DIZAINE {i} – Concept : Exemple concept {i}**\n"
                    mock += f"**1. Méditation** : Description du concept {i} (à personnaliser).\n"
                    mock += "**2. Notre Père (3x)** : Quelle est la clé de ce concept ?\n"
                    mock += "**3. Je vous salue Marie (10x)** : Phrase de synthèse avec plusieurs mots clés.\n"
                    mock += "**4. Gloire au Père (3x)** : Le concept est connu et consolidé.\n\n"
                mock += "Chapelet Tazzz Bot – Basé sur la plasticité cérébrale.\nCopyright Dr Tazemda"
                return jsonify({'chapelet': mock, 'warning': f'API DeepSeek indisponible : {str(e)}'})
        elif mode == 'personnel':
            defauts = data.get('defauts')
            if not defauts or len(defauts) != 5:
                return jsonify({'error': '5 défauts requis'}), 400
            defauts_str = "\n".join(f"{i+1}. {d}" for i,d in enumerate(defauts))
            prompt = PROMPT_PERSONNEL.format(defauts=defauts_str)
            raw = call_deepseek(prompt)
            chapelet = clean_markdown(raw)
            return jsonify({'chapelet': chapelet})

        elif mode == 'consultation':
            message = data.get('message')
            if not message:
                return jsonify({'error': 'Message requis'}), 400
            classify_prompt = PROMPT_CLASSIFY.format(message)
            raw_class = call_deepseek(classify_prompt, system_message="Retourne uniquement du JSON valide.")
            raw_class = clean_markdown(raw_class)
            json_str = extract_json(raw_class)
            classification = json.loads(json_str)
            type_demande = classification.get('type')
            contenu = classification.get('contenu')

            if type_demande == "expertise":
                domaine = contenu if isinstance(contenu, str) else message[:100]
                prompt = PROMPT_EXPERTISE.format(domaine=domaine)
                type_aff = "EXPERTISE"
            else:
                if not isinstance(contenu, list) or len(contenu) != 5:
                    contenu = ["Je manque de discipline"] * 5
                defauts_str = "\n".join(f"{i+1}. {d}" for i,d in enumerate(contenu[:5]))
                prompt = PROMPT_PERSONNEL.format(defauts=defauts_str)
                type_aff = "PERSONNEL"

            raw = call_deepseek(prompt)
            chapelet = clean_markdown(raw)
            return jsonify({
                'chapelet': chapelet,
                'type_detecte': type_demande,
                'message_info': f"🔍 Type détecté : {type_aff}"
            })
        else:
            return jsonify({'error': 'Mode invalide'}), 400

    except Exception as e:
        print("="*50)
        print("ERREUR DANS /generate")
        traceback.print_exc()
        print("="*50)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
