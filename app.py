import os
import re
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tazbot-secret-key")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

def call_deepseek(prompt, system_message="Tu es un expert pédagogique qui génère des chapelets d'apprentissage."):
    if not DEEPSEEK_API_KEY:
        raise Exception("Clé API manquante")
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2500   # réduit pour accélérer
    }
    resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=120)
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"API error {resp.status_code}: {resp.text[:200]}")

def clean_markdown(text):
    return re.sub(r'```[\s\S]*?```', '', text).replace('`', '').strip()

# ---------- PROMPTS COURTS MAIS PRÉCIS ----------
PROMPT_EXPERTISE = """
Génère un CHAPELET TAZZZ BOT – MODE EXPERTISE (7 jours) pour le domaine : {domaine}.

Structure exacte (à copier) :

**Règle d’or** : (une phrase)
**Point d’entrée** : (une question)

--- Jour 1 – Découverte des bases ---
**DIZAINE 1 – Concept : (nom)**
**1) Méditation (grande fiche)**  
*Instruction : Tenez le gros grain. Lisez ce paragraphe comme une fiche de cours.*  
(Paragraphe dense avec définitions, exemples.)
**2) Notre Père**  
*Récitez 3 fois.*  
« (question problématique) »
**3) Je vous salue Marie**  
*Répétez 10 fois (5 lectures, 5 sans regarder).*  
(Paragraphe synthétique de plusieurs phrases.)
**4) Gloire au Père**  
*Récitez 3 fois.*  
« Le concept (nom) est connu et consolidé. »

(5 dizaines par jour, jours 2 à 7 avec titres : Approfondissement, Cas complexes, Contrôle, Risques, Synthèse, Auto‑évaluation)

Termine par : Chapelet Tazzz Bot – © Dr Tazemda
"""

PROMPT_PERSONNEL = """
Génère un chapelet développement personnel pour ces 5 défauts : {defauts}
Structure : Début (signe de croix, crucifix, 3 Ave, Gloire), puis 5 mystères (un par défaut : méditation (passé+visualisation), Notre Père (3x) : "Mon cerveau, par sa plasticité..." , Je vous salue Marie (10x) : (une phrase courte résumant les 5 défauts), Gloire (3x) : "Je remercie Dieu...". Fin (Salve Regina, mantra final). Termine par © Dr Tazemda.
"""

# ---------- FALLBACK ----------
def fallback_expertise(domaine):
    return f"--- Mode dégradé (API indisponible) ---\nChapelet générique pour {domaine}. Vérifiez clé API et crédit."

# ---------- ROUTES ----------
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
                print("Erreur API, fallback:", e)
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
            # Simple détection mots-clés
            if any(w in message.lower() for w in ['maîtriser', 'apprendre', 'domaine', 'entretien', 'concept', 'recherche']):
                prompt = PROMPT_EXPERTISE.format(domaine=message[:150])
                raw = call_deepseek(prompt)
                chapelet = clean_markdown(raw)
                return jsonify({'chapelet': chapelet, 'message_info': '🔍 Type : EXPERTISE'})
            else:
                return jsonify({'error': 'Pour le personnel, utilisez le mode dédié.'}), 400
        else:
            return jsonify({'error': 'Mode invalide'}), 400
    except Exception as e:
        print("Erreur serveur:", e)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
