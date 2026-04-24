import os
import re
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tazbot-secret-key")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

def call_deepseek(prompt, system_message="Tu es un expert pédagogique."):
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
        "max_tokens": 7000
    }
    resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=90)
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"API error {resp.status_code}: {resp.text[:200]}")

def clean_markdown(text):
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = text.replace('`', '')
    return text.strip()

# ------------------ PROMPT EXPERTISE (basé sur l'exemple utilisateur) ------------------
PROMPT_EXPERTISE = """
Tu vas générer un CHAPELET TAZZZ BOT – MODE EXPERTISE (7 jours) pour le domaine : « {domaine} ».

Objectif : Produire un chapelet d'apprentissage structuré exactement comme dans l'exemple suivant (recherche clinique).

### FORMAT EXIGÉ (à copier strictement) :

**Règle d'or** : (une phrase percutante sur le domaine)

**Point d'entrée du problème** : (une question centrale)

--- **Jour 1 – (titre)** ---

**DIZAINE 1 – Concept : (nom du concept)**  

**1) Méditation (grande fiche)**  
*Instruction : Tenez le gros grain. Lisez ce paragraphe lentement, comme une fiche de cours. Vous pouvez aussi le relire plusieurs fois, revoir vos notes personnelles ou consulter d’autres sources.*  
(Paragraphe dense : définition, exemples, points clés, peut contenir des tableaux en texte brut.)

**2) Notre Père**  
*Récitez cette question 3 fois (à voix haute ou mentalement).*  
« (Question problématique sur le concept) »

**3) Je vous salue Marie**  
*Répétez ce paragraphe 10 fois (5 fois en lecture et 5 fois sans regarder). Lisez‑le d’abord pour bien l’ancrer.*  
(Paragraphe synthétique, plusieurs phrases.)

**4) Gloire au Père**  
*Récitez cette phrase 3 fois.*  
« Le concept “(nom du concept)” est connu et consolidé. »

(répéter pour 5 dizaines par jour, sur 7 jours. Les titres des jours : Découverte des bases, Approfondissement opérationnel, Cas complexes, Contrôle qualité, Gestion des risques, Synthèse, Auto‑évaluation.)

Termine par : "Chapelet Tazzz Bot – Basé sur la plasticité cérébrale et la répétition rythmée. © Dr Tazemda"
"""

# ------------------ PROMPT PERSONNEL ------------------
PROMPT_PERSONNEL = """
Génère un CHAPELET TAZZZ BOT – MODE DÉVELOPPEMENT PERSONNEL pour ces 5 défauts :
{defauts}

Structure :
> *Munissez-vous d'un chapelet pour égrener chaque grain...*

### DÉBUT
- Signe de croix : "Au nom de mon engagement, de ma lucidité et de ma persévérance."
- Crucifix : "Je ne subis plus ma vie."
- 3 Ave initiaux (listés)
- Gloire

### 5 MYSTÈRES
Pour chaque défaut :
**Mystère X – (défaut)**
**Méditation** : (passé négatif + visualisation positive)
**Notre Père** : "Mon cerveau, par sa plasticité infinie..." *(à répéter 3 fois)*
**Je vous salue Marie** : (une phrase courte unique résumant la correction des 5 défauts) *(à répéter 10 fois)*
**Gloire au Père** : "Je remercie Dieu et l'univers..." *(à répéter 3 fois)*

### FIN
Salve Regina, mantra final, signe de croix.

Termine par : "Chapelet Tazzz Bot – Basé sur la plasticité cérébrale et la répétition rythmée. © Dr Tazemda"
"""

# ------------------ FALLBACK (si API échoue) ------------------
def fallback_expertise(domaine):
    return f"""--- MODE DÉGRADÉ (API indisponible) ---
Chapelet générique pour {domaine}.
Veuillez vérifier votre clé API ou votre crédit DeepSeek.
(Structure non générée automatiquement pour l'instant. Réessayez plus tard.)"""

# ------------------ ROUTES ------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    mode = data.get('mode')
    try:
        if mode == 'expertise':
            domaine = data.get('domaine')
            if not domaine:
                return jsonify({'error': 'Domaine requis'}), 400
            prompt = PROMPT_EXPERTISE.format(domaine=domaine)
            try:
                raw = call_deepseek(prompt)
                chapelet = clean_markdown(raw)
            except Exception as e:
                print("Erreur API:", e)
                chapelet = fallback_expertise(domaine)
            return jsonify({'chapelet': chapelet})

        elif mode == 'personnel':
            defauts = data.get('defauts')
            if not defauts or len(defauts) != 5:
                return jsonify({'error': '5 défauts requis'}), 400
            prompt = PROMPT_PERSONNEL.format(defauts="\n".join(defauts))
            raw = call_deepseek(prompt)
            chapelet = clean_markdown(raw)
            return jsonify({'chapelet': chapelet})

        elif mode == 'consultation':
            message = data.get('message')
            if not message:
                return jsonify({'error': 'Message requis'}), 400
            # Détection simple par mots-clés
            if any(w in message.lower() for w in ['maîtriser', 'apprendre', 'domaine', 'entretien', 'concept', 'IT support', 'recherche clinique']):
                domaine = message[:150]
                prompt = PROMPT_EXPERTISE.format(domaine=domaine)
                raw = call_deepseek(prompt)
                chapelet = clean_markdown(raw)
                return jsonify({'chapelet': chapelet, 'message_info': '🔍 Type détecté : EXPERTISE'})
            else:
                # Sinon on suppose personnel (l'utilisateur décrit des défauts)
                # Pour un vrai traitement, on demanderait les 5 défauts, mais en consultation on peut générer des défauts fictifs.
                # Ici, pour rester simple, on renvoie un message invitant à utiliser le mode personnel.
                return jsonify({'error': 'Pour du développement personnel, utilisez le mode "Développement personnel" (avec 5 défauts).'}), 400

        else:
            return jsonify({'error': 'Mode invalide'}), 400
    except Exception as e:
        print("Erreur serveur:", e)
        return jsonify({'error': f'Erreur interne : {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
