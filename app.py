import os
import json
import requests
from flask import Flask, request, render_template, jsonify, session
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tazbot-secret-key-change-in-production")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# ================= FONCTIONS D'APPEL À DEEPSEEK =================
def call_deepseek(prompt, system_message="Tu es l'assistant Taz Bot, spécialiste des chapelets de transformation."):
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
        "max_tokens": 3500
    }
    response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"Erreur API DeepSeek: {response.status_code} - {response.text}")

# ================= PROMPTS =================
PROMPT_EXPERTISE = """
Tu vas générer un CHAPELET TAZ BOT – MODE EXPERTISE (7 jours).

L'utilisateur souhaite maîtriser le domaine suivant : {domaine}.

Structure à respecter (détaillée dans la synopsis technique) :

- **Rappel** des acquis de la semaine précédente (s'il y a un lien, sinon ignorer)
- **Point d'entrée du problème** (une phrase qui pose la question centrale)
- **Règle d'or de la semaine** (une phrase positive)
- **5 dizaines** (une par concept clé du domaine à définir par toi)
  Pour chaque dizaine :
    - **Méditation** : grande fiche (définition, rôle, approche, application concrète)
    - **Notre Père** : problème général + problème illustratif (avec ?)
    - **Je vous salue Marie (10x identique)** : mantra spécifique au concept (général → exemple)
    - **Gloire au Père** : mini-consolidation
- **Clôture de la journée** (une phrase de synthèse)

Soigne la qualité pédagogique, sans négation. Utilise l'exemple du domaine pour chaque mantra.
Renvoie uniquement le texte du chapelet, prêt à être imprimé ou lu.
"""

PROMPT_PERSONNEL = """
Tu vas générer un CHAPELET TAZ BOT – MODE DÉVELOPPEMENT PERSONNEL (21 ou 66 jours).

L'utilisateur décrit 5 défauts à corriger (ou 5 qualités à acquérir) :
{defauts}

Construis un chapelet complet selon la structure canonique suivante (texte à renvoyer directement) :

### DÉBUT (crucifix et premiers grains)
- Signe de croix : "Au nom de mon engagement, de ma lucidité et de ma persévérance."
- Crucifix (1 grain) : "Je ne subis plus ma vie. Je deviens l'acteur de chaque heure."
- 3 Ave initiaux :
  1. "Je laisse derrière moi le poids des errances passées."
  2. "Je choisis la constance dans l'action, si petite soit-elle."
  3. "Je mérite un travail, une stabilité, une fierté retrouvée."
- Gloire : "Je rends grâce à la vie pour ce nouveau départ."

### 5 MYSTÈRES (un par défaut)
Pour chaque défaut (dans l'ordre donné), écris :

**Mystère [numéro] – [intitulé du défaut]**

**Méditation** :  
- Rappelle une situation passée typique où ce défaut a causé un problème (factuel, sans jugement).  
- Puis visualisation positive du comportement opposé réussi.

**Notre Père** (identique pour tous les mystères) :  
"Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes. Je choisis ma lucidité."

**10 × Je vous salue Marie** (mantra UNIQUE pour tout le chapelet) :  
[Invente une phrase courte (max 15 mots) qui résume la correction des 5 défauts. Exemple : "Je me lève tôt, je termine ce que je commence, je sors chaque jour, je structure ma vie, j'attire un travail stable et prospère."]

**Gloire au Père** (identique) :  
"Je remercie Dieu et l'univers pour cette transformation profonde."

### FIN DU CHAPELET
- Salve Regina : "Ô volonté retrouvée, sois ma lumière et ma force."
- Mantra final : "Ce chapelet de 21 jours ancre en moi la discipline joyeuse et l'action efficace."
- Signe de croix final : "Au nom de mon engagement, de ma lucidité et de ma persévérance – ainsi soit-il."

IMPORTANT : Aucune phrase négative. Le mantra "Je vous salue Marie" doit être IDENTIQUE pour les 5 mystères.
Renvoie uniquement le texte du chapelet.
"""

PROMPT_CONSULTATION = """
L'utilisateur a exprimé un besoin vague : "{message_utilisateur}"

Analyse ce message et extrait 5 défauts ou axes de travail personnalisés (un par ligne, sous forme de phrases courtes sans négation, comme "Je me lève tard" → "Je me lève tôt").

Les 5 axes doivent être concrets, actionnables et découler directement du récit.

Retourne uniquement ces 5 phrases, une par ligne, précédées d'un titre "AXES IDENTIFIÉS :".
"""

# ================= ROUTES FLASK =================
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
            chapelet = call_deepseek(prompt)
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
            chapelet = call_deepseek(prompt)
            return jsonify({'chapelet': chapelet})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    elif mode == 'consultation':
        message = data.get('message')
        if not message:
            return jsonify({'error': 'Message requis'}), 400
        prompt = PROMPT_CONSULTATION.format(message_utilisateur=message)
        try:
            reponse = call_deepseek(prompt)
            # Extraction des axes
            lignes = reponse.strip().split("\n")
            axes = [l for l in lignes if not l.startswith("AXES IDENTIFIÉS") and l.strip() != ""]
            if len(axes) >= 5:
                axes = axes[:5]
                # Générer automatiquement le chapelet personnel
                defauts_str = "\n".join(f"{i+1}. {a}" for i,a in enumerate(axes))
                prompt_perso = PROMPT_PERSONNEL.format(defauts=defauts_str)
                chapelet = call_deepseek(prompt_perso)
                return jsonify({'chapelet': chapelet, 'axes': axes})
            else:
                return jsonify({'error': 'Impossible d\'extraire 5 axes', 'raw': reponse}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    else:
        return jsonify({'error': 'Mode invalide'}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
