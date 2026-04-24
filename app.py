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
        raise Exception("Clé API DeepSeek manquante")
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2500
    }
    resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=120)
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"API error {resp.status_code}: {resp.text[:200]}")

def clean_markdown(text):
    return re.sub(r'```[\s\S]*?```', '', text).replace('`', '').strip()

# Titres des jours (objectifs)
JOURS_TITRES = {
    1: "Découvrir les origines et les grandes voies de création",
    2: "Maîtriser les grandes phases du développement préclinique et clinique",
    3: "Comprendre la compétition mondiale et le cycle de financement",
    4: "Appréhender le cadre juridique français (Loi Jardé, Bioéthique, RGPD)",
    5: "Intégrer le règlement européen RE 536/2014 (essais cliniques)",
    6: "Connaître les dispositifs médicaux (DM) et DMDIV",
    7: "Synthétiser tout le parcours pour obtenir l'AMM"
}

PROMPT_JOUR = """
Tu es un expert en pédagogie. Génère le **Jour {jour_num} – Objectif : {objectif}** d’un chapelet d’apprentissage sur le domaine : « {domaine} ».

Le chapelet complet comporte 7 jours. Pour le jour demandé, produit exactement le format suivant (5 dizaines) :

--- Jour {jour_num} – Objectif : {objectif} ---

**DIZAINE 1 – Concept : (nom)**

**1) Méditation (grande fiche)**  
*Instruction : Tenez le gros grain. Lisez ce paragraphe comme une fiche de cours.*  
(Paragraphe dense : définitions, exemples, points clés.)

**2) Notre Père**  
*Récitez cette question 3 fois.*  
« (Question problématique) »

**3) Je vous salue Marie**  
*Répétez ce paragraphe 10 fois (5 lectures, 5 sans regarder).*  
(Paragraphe synthétique résumant le concept.)

**4) Gloire au Père**  
*Récitez cette phrase 3 fois.*  
« Le concept (nom) est connu et consolidé. »

(Recommence pour DIZAINE 2 à 5 avec des concepts différents et cohérents avec le thème du jour.)

Termine par : (rien de plus, pas de copyright ici).
"""

def generer_jour(domaine, jour_num):
    objectif = JOURS_TITRES.get(jour_num, "Apprentissage")
    prompt = PROMPT_JOUR.format(jour_num=jour_num, objectif=objectif, domaine=domaine)
    raw = call_deepseek(prompt)
    return clean_markdown(raw)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_jour', methods=['POST'])
def generate_jour():
    data = request.get_json()
    domaine = data.get('domaine')
    jour = data.get('jour')
    if not domaine or not jour:
        return jsonify({'error': 'Domaine et jour requis'}), 400
    try:
        contenu = generer_jour(domaine, jour)
        return jsonify({'contenu': contenu})
    except Exception as e:
        print("Erreur génération jour:", e)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
