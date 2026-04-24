import os
import sqlite3
import re
import requests
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tazbot-secret-key")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

def call_deepseek(prompt, system_message="Tu es un expert pédagogique qui génère des chapelets d'apprentissage de haute qualité."):
    if not DEEPSEEK_API_KEY:
        raise Exception("Clé API DeepSeek manquante. Ajoutez DEEPSEEK_API_KEY dans les variables d'environnement.")
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
        "max_tokens": 4500
    }
    try:
        resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=90)
    except requests.exceptions.Timeout:
        raise Exception("Timeout : DeepSeek ne répond pas après 90 secondes.")
    if resp.status_code == 200:
        # Vérifie que la réponse est du JSON valide
        try:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise Exception(f"Réponse inattendue de l'API : {resp.text[:200]}")
    else:
        # Affiche le code d'erreur et le message pour diagnostic
        raise Exception(f"API DeepSeek error {resp.status_code}: {resp.text[:500]}")

def clean_markdown(text):
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = text.replace('`', '')
    return text.strip()

# ------------------ FALLBACK (chapelet de secours complet) ------------------
def generate_fallback_expertise(domaine):
    return f"""
--- CHAPELET TAZZZ BOT – EXPERTISE (7 jours) ---
Mode dégradé (API injoignable). Voici un chapelet générique pour "{domaine}".

**--- Jour 1 – Découverte des bases ---**

**DIZAINE 1 – Concept : Fondamentaux de {domaine}**  
**1) Méditation** : Pour maîtriser {domaine}, il faut d'abord en connaître les objectifs et les principaux acteurs.  
**2) Notre Père** : Quels sont les trois piliers de {domaine} ?  
**3) Je vous salue Marie** : Je retiens que {domaine} repose sur la connaissance des règles, des bonnes pratiques et des outils. Je répète cela chaque jour.  
**4) Gloire au Père** : Le concept "fondamentaux" est consolidé.

(Structure identique pour les 5 dizaines du jour 1, puis jours 2 à 7 sur le même modèle. En production, ce texte serait plus long, mais l'API est la solution définitive.)
Chapelet Tazzz Bot – Basé sur la plasticité cérébrale et la répétition rythmée.
Copyright Dr Tazemda
"""

# ------------------ PROMPT EXPERTISE (avec instructions de qualité) ------------------
PROMPT_EXPERTISE = f"""
Tu vas générer un CHAPELET TAZZZ BOT – MODE EXPERTISE (7 jours) pour le domaine : {{domaine}}.

Chaque jour contient 5 dizaines. Chaque dizaine doit suivre EXACTEMENT ce format :

**DIZAINE X – Concept : [nom du concept]**

**1) Méditation (grande fiche)**  
*Instruction : Tenez le gros grain. Lisez ce paragraphe lentement, comme une fiche de cours. Vous pouvez aussi le relire plusieurs fois, revoir vos notes personnelles ou consulter d’autres sources.*  
[Paragraphe dense, précis, pédagogique – définitions, explications, exemples concrets, points clés.]

**2) Notre Père**  
*Récitez cette question 3 fois (à voix haute ou mentalement).*  
« [Question problématisée, générale, qui invite à réfléchir sur le concept] »

**3) Je vous salue Marie**  
*Répétez ce paragraphe 10 fois (5 fois en lecture et 5 fois sans regarder). Lisez‑le d’abord pour bien l’ancrer.*  
[Paragraphe synthétique de plusieurs phrases, résumant l’essentiel du concept.]

**4) Gloire au Père**  
*Récitez cette phrase 3 fois.*  
« Le concept “[nom du concept]” est connu et consolidé. »

Structure à produire (7 jours avec titres) :
- Jour 1 – Découverte des bases
- Jour 2 – Approfondissement opérationnel
- Jour 3 – Cas complexes et exceptions
- Jour 4 – Contrôle qualité et indicateurs
- Jour 5 – Gestion des risques et plan d'action
- Jour 6 – Synthèse et liens entre concepts
- Jour 7 – Auto‑évaluation et perfectionnement

Termine par : Chapelet Tazzz Bot – Basé sur la plasticité cérébrale et la répétition rythmée. Copyright Dr Tazemda
"""

def generate_expertise_via_api(domaine):
    prompt = PROMPT_EXPERTISE.format(domaine=domaine)
    raw = call_deepseek(prompt)
    return clean_markdown(raw)

# ------------------ MODE PERSONNEL (mock, stable) ------------------
def generate_mock_personnel(defauts):
    mantra = "Je me lève tôt, je termine ce que je commence, je sors chaque jour, je structure ma vie, j'attire un travail stable et prospère."
    texte = f"""
**CHAPELET TAZZZ BOT – MODE DÉVELOPPEMENT PERSONNEL (21/66 jours)**

> Munissez-vous d'un chapelet pour égrener chaque grain correspondant en récitant à voix haute ou mentalement, dans un endroit calme.

### DÉBUT
- Signe de croix : "Au nom de mon engagement, de ma lucidité et de ma persévérance."
- Crucifix : "Je ne subis plus ma vie. Je deviens l'acteur de chaque heure."
- 3 Ave initiaux :  
  1. "Je laisse derrière moi le poids des errances passées."  
  2. "Je choisis la constance dans l'action, si petite soit-elle."  
  3. "Je mérite un travail, une stabilité, une fierté retrouvée."
- Gloire : "Je rends grâce à la vie pour ce nouveau départ."

### 5 MYSTÈRES
"""
    for i, defaut in enumerate(defauts, 1):
        texte += f"""
**Mystère {i} – {defaut}**  
**Méditation** : (souvenir d’une situation où ce défaut a nui) … Aujourd’hui, je visualise le comportement opposé réussi.  
**Notre Père** : "Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes. Je choisis ma lucidité." *(à répéter 3 fois)*  
**Je vous salue Marie** : {mantra} *(à répéter 10 fois)*  
**Gloire au Père** : "Je remercie Dieu et l'univers pour ses réalisations dans ma vie et cette transformation profonde." *(à répéter 3 fois)*
"""
    texte += """
### FIN
- Salve Regina : "Ô volonté retrouvée, sois ma lumière et ma force."
- Mantra final : "Ce chapelet de 21 jours ancre en moi la discipline joyeuse et l'action efficace."
- Signe de croix final.

Chapelet Tazzz Bot – Basé sur la plasticité cérébrale et la répétition rythmée.
Copyright Dr Tazemda
"""
    return texte

# ------------------ BASE DE DONNÉES ------------------
def init_db():
    conn = sqlite3.connect('tazbot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS chapelets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT,
                  mode TEXT,
                  input TEXT,
                  contenu TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS feedback
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT,
                  note INTEGER,
                  commentaire TEXT)''')
    conn.commit()
    conn.close()

init_db()

def sauvegarder_chapelet(mode, input_utilisateur, contenu):
    conn = sqlite3.connect('tazbot.db')
    c = conn.cursor()
    c.execute("INSERT INTO chapelets (date, mode, input, contenu) VALUES (?, ?, ?, ?)",
              (str(datetime.now()), mode, input_utilisateur, contenu))
    conn.commit()
    conn.close()

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
            try:
                chapelet = generate_expertise_via_api(domaine)
                status = "API"
            except Exception as e:
                print("Erreur API, fallback activé:", e)
                chapelet = generate_fallback_expertise(domaine)
                status = "fallback"
            sauvegarder_chapelet('expertise', domaine, chapelet)
            return jsonify({'chapelet': chapelet, 'status': status})

        elif mode == 'personnel':
            defauts = data.get('defauts')
            if not defauts or len(defauts) != 5:
                return jsonify({'error': '5 défauts requis'}), 400
            chapelet = generate_mock_personnel(defauts)
            sauvegarder_chapelet('personnel', str(defauts), chapelet)
            return jsonify({'chapelet': chapelet})

        elif mode == 'consultation':
            message = data.get('message')
            if not message:
                return jsonify({'error': 'Message requis'}), 400
            if any(w in message.lower() for w in ['maîtriser', 'apprendre', 'domaine', 'entretien', 'comprendre']):
                domaine = message[:150]
                try:
                    chapelet = generate_expertise_via_api(domaine)
                except Exception as e:
                    print("Erreur API consultation, fallback:", e)
                    chapelet = generate_fallback_expertise(domaine)
                sauvegarder_chapelet('consultation_expertise', message, chapelet)
                return jsonify({'chapelet': chapelet, 'message_info': '🔍 Type détecté : EXPERTISE'})
            else:
                defauts = ["Je manque de discipline"] * 5
                chapelet = generate_mock_personnel(defauts)
                sauvegarder_chapelet('consultation_personnel', message, chapelet)
                return jsonify({'chapelet': chapelet, 'message_info': '🔍 Type détecté : PERSONNEL'})
        else:
            return jsonify({'error': 'Mode invalide'}), 400

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'error': f'Erreur interne : {str(e)}'}), 500

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
