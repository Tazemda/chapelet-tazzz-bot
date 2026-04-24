import os
import json
import re
import requests
from flask import Flask, request, render_template, jsonify

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
        "max_tokens": 5000
    }
    resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload)
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

# ------------------ PROMPT EXPERTISE (structure type recherche clinique) ------------------
PROMPT_EXPERTISE = """
Génère un CHAPELET TAZZZ BOT – MODE EXPERTISE (7 jours) pour le domaine : {domaine}.

Le chapelet est un outil de mémorisation active par répétition rythmée, basé sur la plasticité cérébrale.
Chaque jour comporte 5 dizaines. Chaque dizaine suit EXACTEMENT ce modèle (à copier) :

**DIZAINE X – Concept : [nom du concept]**

**1. Méditation sur le mystère** :  
*Grande fiche – détaillée à lire simplement (en tenant le gros grain correspondant).*  
(Écris ici un paragraphe dense et clair, avec définition, rôle, exemples, points de repère.)

**2. Notre Père (à répéter 3 fois)** :  
(Formule une question problématique ou un aide-mémoire, par exemple : « Mon Dieu, aide-moi à ne pas confondre... » ou « Comment vérifier que... ? »)

**3. Je vous salue Marie (à répéter 10 fois)** :  
(Ton mantra doit être un **paragraphe de plusieurs phrases** qui synthétise tout le concept. Exemple tiré du cours de recherche clinique :  
« P c’est la Population avec ses critères d’inclusion. Exemple : HSH séronégatifs à haut risque.  
I c’est l’Intervention précise et reproductible. Exemple : spiruline 500 mg par jour.  
C c’est le Comparateur pertinent. Exemple : placebo identique.  
O c’est l’Outcome mesurable et clinique. Exemple : incidence du VIH à 12 mois par ELISA et Western blot. »  
Adapte ce style au concept traité. Ce paragraphe sera lu ou récité 10 fois, il doit être riche et complet.)

**4. Gloire au Père (à répéter 3 fois)** :  
« Le concept « X » est connu et consolidé. »

Sépare les jours par : **--- Jour 1 – [titre] ---** , etc. (Jour 1 à Jour 7, avec titres adaptés au domaine : découverte, méthodes, cas pratiques, etc.)

Termine l’ensemble par :
Chapelet Tazzz Bot – Basé sur la plasticité cérébrale et la répétition rythmée.
Copyright Dr Tazemda
"""

# ------------------ PROMPT PERSONNEL (inchangé, mantra court) ------------------
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
**10 × Je vous salue Marie** (mantra unique pour tous les mystères, une phrase courte résumant la correction des 5 défauts, à répéter 10 fois) : (ici la phrase)
**Gloire au Père** (à répéter 3 fois) : "Je remercie Dieu et l'univers pour ses réalisations dans ma vie et cette transformation profonde."

### FIN
- Salve Regina, Mantra final, Signe de croix final.

Termine par :
Chapelet Tazzz Bot – Basé sur la plasticité cérébrale et la répétition rythmée.
Copyright Dr Tazemda
"""

# ------------------ PROMPT CLASSIFICATION (simple, plus fiable) ------------------
PROMPT_CLASSIFY = """
Réponds uniquement par un objet JSON valide, sans texte avant ou après.

Message reçu : "{}"

Règles :
- Si l'utilisateur veut APPRENDRE, MAÎTRISER, COMPRENDRE un domaine technique ou professionnel → type = "expertise", contenu = le nom du domaine.
- Sinon (défauts personnels : lenteur, procrastination, timidité, désordre...) → type = "personnel", contenu = liste de 5 défauts.

Exemples :
Message: "Je veux maîtriser l'audit des services d'aide à domicile" → {{"type": "expertise", "contenu": "Audit des services d'aide à domicile"}}
Message: "Je me lève tard, je suis paresseux, je dépense trop, je suis timide, je manque de motivation" → {{"type": "personnel", "contenu": ["Je me lève tard", "Je suis paresseux", "Je dépense trop", "Je suis timide", "Je manque de motivation"]}}
"""

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
        prompt = PROMPT_EXPERTISE.format(domaine=domaine)
        try:
            raw = call_deepseek(prompt)
            chapelet = clean_markdown(raw)
            return jsonify({'chapelet': chapelet})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    elif mode == 'personnel':
        defauts = data.get('defauts')
        if not defauts or len(defauts) != 5:
            return jsonify({'error': '5 défauts requis'}), 400
        defauts_str = "\n".join(f"{i+1}. {d}" for i,d in enumerate(defauts))
        prompt = PROMPT_PERSONNEL.format(defauts=defauts_str)
        try:
            raw = call_deepseek(prompt)
            chapelet = clean_markdown(raw)
            return jsonify({'chapelet': chapelet})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    elif mode == 'consultation':
        message = data.get('message')
        if not message:
            return jsonify({'error': 'Message requis'}), 400

        classify_prompt = PROMPT_CLASSIFY.format(message)
        try:
            raw_class = call_deepseek(classify_prompt, system_message="Retourne uniquement du JSON valide.")
            raw_class = clean_markdown(raw_class)
            json_str = extract_json(raw_class)
            classification = json.loads(json_str)
            type_demande = classification.get('type')
            contenu = classification.get('contenu')
        except Exception as e:
            # Fallback mots-clés
            if any(word in message.lower() for word in ['maîtriser', 'apprendre', 'comprendre', 'entretien', 'formation', 'concepts', 'niveau', 'domaine']):
                type_demande = "expertise"
                contenu = message
            else:
                type_demande = "personnel"
                contenu = ["Je manque de discipline"] * 5

        if type_demande == "expertise":
            domaine = contenu if isinstance(contenu, str) else message
            prompt = PROMPT_EXPERTISE.format(domaine=domaine)
            type_aff = "EXPERTISE"
        else:
            if not isinstance(contenu, list) or len(contenu) != 5:
                contenu = ["Je manque de discipline"] * 5
            defauts_str = "\n".join(f"{i+1}. {d}" for i,d in enumerate(contenu[:5]))
            prompt = PROMPT_PERSONNEL.format(defauts=defauts_str)
            type_aff = "PERSONNEL"

        try:
            raw = call_deepseek(prompt)
            chapelet = clean_markdown(raw)
            return jsonify({
                'chapelet': chapelet,
                'type_detecte': type_demande,
                'message_info': f"🔍 Type détecté : {type_aff}"
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    else:
        return jsonify({'error': 'Mode invalide'}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
