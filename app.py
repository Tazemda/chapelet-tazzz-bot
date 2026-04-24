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
        "max_tokens": 4000
    }
    resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload)
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"API DeepSeek error {resp.status_code}: {resp.text}")

def clean_markdown(text):
    # Supprime les blocs de code markdown
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = text.replace('`', '')
    return text.strip()

PROMPT_EXPERTISE = f"""
Génère un CHAPELET TAZZZ BOT – MODE EXPERTISE (7 jours) pour le domaine : {{domaine}}.

Structure à respecter (texte brut, pas de markdown) :

- **Rappel** (si utile)
- **Point d'entrée du problème**
- **Règle d'or**
- **5 dizaines** (une par concept clé). Pour chaque :
   - **Méditation (lecture simple – vous pouvez consulter vos notes de cours personnelles ou d'autres sources pour une exposition générale)** : (définition, rôle, exemple)
   - **Notre Père** (problème général + illustratif avec ?)
   - **Je vous salue Marie (10x identique)** (mantra spécifique au concept)
   - **Gloire au Père** : "Je remercie Dieu et l'univers pour ses réalisations dans ma vie et cette transformation profonde."
- **Clôture**

Termine par :
Chapelet Tazzz Bot – Basé sur la plasticité cérébrale et la répétition rythmée.
Copyright Dr Tazemda
"""

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
**Notre Père** : "Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes. Je choisis ma lucidité."
**10 × Je vous salue Marie** : (un mantra unique pour tous les mystères, résumant la correction des 5 défauts)
**Gloire au Père** : "Je remercie Dieu et l'univers pour ses réalisations dans ma vie et cette transformation profonde."

### FIN
- Salve Regina, Mantra final, Signe de croix final.

Termine par :
Chapelet Tazzz Bot – Basé sur la plasticité cérébrale et la répétition rythmée.
Copyright Dr Tazemda
"""

PROMPT_CLASSIFY = """
Tu es un classificateur. Réponds UNIQUEMENT par un objet JSON valide, sans texte avant ou après.

Analyse le message de l'utilisateur :

"{}"

Règles :
- Si l'utilisateur veut APPRENDRE une compétence technique, MAÎTRISER un domaine, PRÉPARER un entretien sur des connaissances (ex: IT support, python, comptabilité) → type = "expertise", contenu = le nom du domaine (une phrase courte).
- Sinon, s'il parle de défauts personnels (lenteur, procrastination, timidité, désordre, manque de motivation) → type = "personnel", contenu = une liste de 5 défauts (sous forme de tableau JSON).

EXEMPLES :
Message: "Je veux maîtriser les concepts du IT support niveau 1 et 2 pour un entretien"
→ {{"type": "expertise", "contenu": "IT support niveau 1 et 2"}}

Message: "Je me lève tard, je suis paresseux, je dépense trop, je suis timide, je manque de motivation"
→ {{"type": "personnel", "contenu": ["Je me lève tard", "Je suis paresseux", "Je dépense trop", "Je suis timide", "Je manque de motivation"]}}

Important : Ne mets PAS de sauts de ligne parasites dans le JSON. Utilise les guillemets doubles.
""".strip()

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

        # Classification renforcée
        classify_prompt = PROMPT_CLASSIFY.format(message)
        try:
            raw_class = call_deepseek(classify_prompt, system_message="Tu retournes uniquement du JSON valide, sans aucun autre texte.")
            raw_class = clean_markdown(raw_class)
            # Cherche un objet JSON valide
            start = raw_class.find('{')
            end = raw_class.rfind('}') + 1
            if start == -1 or end == 0:
                raise ValueError("Aucun JSON trouvé")
            json_str = raw_class[start:end]
            classification = json.loads(json_str)
            type_demande = classification.get('type')
            contenu = classification.get('contenu')
        except Exception as e:
            # Fallback : on essaie de détecter grossièrement
            if any(word in message.lower() for word in ['maîtriser', 'apprendre', 'comprendre', 'entretien', 'niveau 1', 'niveau 2', 'formation', 'concepts']):
                type_demande = "expertise"
                contenu = message  # on utilisera le message brut comme domaine
            else:
                type_demande = "personnel"
                contenu = ["Je manque de discipline"] * 5

        # Génération du chapelet selon le type
        if type_demande == "expertise":
            domaine = contenu if isinstance(contenu, str) else message
            prompt = PROMPT_EXPERTISE.format(domaine=domaine)
        else:
            if not isinstance(contenu, list) or len(contenu) != 5:
                contenu = ["Je manque de discipline"] * 5
            defauts_str = "\n".join(f"{i+1}. {d}" for i,d in enumerate(contenu[:5]))
            prompt = PROMPT_PERSONNEL.format(defauts=defauts_str)

        try:
            raw = call_deepseek(prompt)
            chapelet = clean_markdown(raw)
            return jsonify({
                'chapelet': chapelet,
                'type_detecte': type_demande,
                'message_info': f"🔍 Type détecté : {'EXPERTISE' if type_demande == 'expertise' else 'PERSONNEL'}"
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    else:
        return jsonify({'error': 'Mode invalide'}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
      
