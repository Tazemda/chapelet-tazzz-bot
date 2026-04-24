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
        "max_tokens": 8000  # augmenté pour 7 jours
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

# ------------------ PROMPT EXPERTISE (7 jours, structure par dizaine) ------------------
PROMPT_EXPERTISE = """
Tu vas générer un CHAPELET TAZZZ BOT – MODE EXPERTISE pour maîtriser le domaine : {domaine}.

Ce chapelet se pratique sur **7 jours**. Chaque jour correspond à un objectif d’apprentissage différent, avec 5 dizaines (concepts clés).  
Au total, tu produiras 35 dizaines (5 par jour).

Structure pour **chaque dizaine** (respecte impérativement ce format) :

**DIZAINE X – Concept : [nom du concept]**

**1. Méditation sur le mystère** :  
*Grande fiche – détaillée à lire simplement (en tenant le gros grain correspondant).*  
(Donne une explication claire, des définitions, des exemples, des points de repère – comme une mini‑fiche de cours.)

**2. Notre Père (à répéter 3 fois)** :  
(une question ou un problème général formulé comme une prière, par exemple : « Mon Dieu, aide-moi à ne pas confondre... » ou « Quelle est la bonne méthode pour... ? »)

**3. Je vous salue Marie (à répéter 10 fois)** :  
(une phrase courte, positive, qui synthétise l’essentiel du concept. Exemple : « Ma déclaration est déposée avant la date légale, sans stress ni retard. »)

**4. Gloire au Père (à répéter 3 fois)** :  
(une phrase de consolidation du type : « Le concept « X » est connu et consolidé. »)

Entre les jours, sépare avec : **--- Jour X ---** et un titre (ex: **Jour 1 – Découverte des bases**).

Contenu à générer :

- **Jour 1** : Concepts fondamentaux (définitions, principes de base)
- **Jour 2** : Méthodologie et outils clés
- **Jour 3** : Application pratique et cas courants
- **Jour 4** : Cas complexes et exceptions
- **Jour 5** : Contrôle, audit et indicateurs
- **Jour 6** : Synthèse et liens entre concepts
- **Jour 7** : Auto‑évaluation et préparation à l’expertise

Soigne la qualité pédagogique. Chaque méditation doit être dense mais claire. Les mantras (Je vous salue Marie) doivent être positifs, courts, spécifiques au concept. Les questions du Notre Père doivent provoquer la réflexion.

Termine l’ensemble par :
Chapelet Tazzz Bot – Basé sur la plasticité cérébrale et la répétition rythmée.
Copyright Dr Tazemda
"""

# ------------------ PROMPT PERSONNEL (inchangé) ------------------
PROMPT_PERSONNEL = f"""
Génère un CHAPELET TAZZZ BOT – MODE DÉVELOPPEMENT PERSONNEL (21 ou 66 jours) pour ces 5 défauts :
{{defauts}}

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
**Notre Père** : "Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes. Je choisis ma lucidité." (à répéter 3 fois)
**10 × Je vous salue Marie** : (un mantra unique pour tous les mystères, résumant la correction des 5 défauts) (à répéter 10 fois)
**Gloire au Père** : "Je remercie Dieu et l'univers pour ses réalisations dans ma vie et cette transformation profonde." (à répéter 3 fois)

### FIN
- Salve Regina, Mantra final, Signe de croix final.

Termine par :
Chapelet Tazzz Bot – Basé sur la plasticité cérébrale et la répétition rythmée.
Copyright Dr Tazemda
"""

# ------------------ PROMPT CLASSIFICATION (inchangé) ------------------
PROMPT_CLASSIFY = """
Tu es un classificateur. Réponds UNIQUEMENT par un objet JSON valide, sans texte avant ou après.

Analyse le message de l'utilisateur :

"{}"

Règles :
- Si l'utilisateur veut APPRENDRE une compétence technique, MAÎTRISER un domaine, PRÉPARER un entretien sur des connaissances → type = "expertise", contenu = le nom du domaine (une phrase courte).
- Sinon (défauts personnels : lenteur, procrastination, timidité, désordre, etc.) → type = "personnel", contenu = une liste de 5 défauts (tableau JSON).

EXEMPLES :
Message: "Je veux maîtriser les concepts du IT support niveau 1 et 2"
→ {{"type": "expertise", "contenu": "IT support niveau 1 et 2"}}

Message: "Je me lève tard, je suis paresseux, je dépense trop, je suis timide, je manque de motivation"
→ {{"type": "personnel", "contenu": ["Je me lève tard", "Je suis paresseux", "Je dépense trop", "Je suis timide", "Je manque de motivation"]}}
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
            start = raw_class.find('{')
            end = raw_class.rfind('}') + 1
            if start == -1 or end == 0:
                raise ValueError("Aucun JSON trouvé")
            json_str = raw_class[start:end]
            classification = json.loads(json_str)
            type_demande = classification.get('type')
            contenu = classification.get('contenu')
        except Exception as e:
            if any(word in message.lower() for word in ['maîtriser', 'apprendre', 'comprendre', 'entretien', 'formation', 'concepts', 'niveau 1', 'niveau 2']):
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
