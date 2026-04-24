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

# ---------- PROMPT POUR UN JOUR (très court) ----------
PROMPT_JOUR = """
Génère le **Jour {jour_num} – {titre}** d’un chapelet d’apprentissage sur le domaine « {domaine} ».
Le plan des 7 jours est :
1: Découverte des bases
2: Approfondissement opérationnel
3: Cas complexes
4: Contrôle qualité
5: Gestion des risques
6: Synthèse
7: Auto‑évaluation

Pour ce jour, produis exactement 5 dizaines au format suivant :

--- Jour {jour_num} – {titre} ---

**DIZAINE 1 – Concept : (nom)**
**1) Méditation (grande fiche)**  
*Instruction : Tenez le gros grain, lisez comme une fiche de cours.*  
(Paragraphe dense, définitions, exemples)
**2) Notre Père**  
*Récitez 3 fois.*  
« (Question problématique) »
**3) Je vous salue Marie**  
*Répétez 10 fois (5 lectures, 5 sans regarder).*  
(Paragraphe synthétique de plusieurs phrases)
**4) Gloire au Père**  
*Récitez 3 fois.*  
« Le concept “(nom)” est connu et consolidé. »

(Recommence pour DIZAINE 2 à 5, avec des concepts différents et adaptés au jour.)
N’ajoute rien d’autre après la dernière dizaine.
"""

def generer_jour(domaine, jour_num):
    titres = [
        "Découverte des bases",
        "Approfondissement opérationnel",
        "Cas complexes et exceptions",
        "Contrôle qualité et indicateurs",
        "Gestion des risques et plan d'action",
        "Synthèse et liens entre concepts",
        "Auto‑évaluation et perfectionnement"
    ]
    titre = titres[jour_num-1]
    prompt = PROMPT_JOUR.format(jour_num=jour_num, titre=titre, domaine=domaine)
    raw = call_deepseek(prompt)
    return clean_markdown(raw)

# ---------- MODE PERSONNEL ----------
PROMPT_PERSONNEL = """
Génère un chapelet développement personnel pour ces 5 défauts :
{defauts}

Structure :
> *Munissez-vous d'un chapelet...*
### DÉBUT
- Signe de croix : "Au nom de mon engagement..."
- Crucifix : "Je ne subis plus ma vie..."
- 3 Ave initiaux
- Gloire
### 5 MYSTÈRES (un par défaut)
Pour chaque défaut :
**Mystère X – (défaut)**
**Méditation** : (souvenir + visualisation positive)
**Notre Père** : "Mon cerveau, par sa plasticité infinie..." *(3 fois)*
**Je vous salue Marie** : (une phrase courte résumant la correction des 5 défauts) *(10 fois)*
**Gloire au Père** : "Je remercie Dieu..." *(3 fois)*
### FIN
Salve Regina, mantra final, signe de croix.
Termine par : © Dr Tazemda
"""

def generer_personnel(defauts):
    prompt = PROMPT_PERSONNEL.format(defauts="\n".join(defauts))
    raw = call_deepseek(prompt)
    return clean_markdown(raw)

# ---------- ROUTES ----------
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

@app.route('/generate_personnel', methods=['POST'])
def generate_personnel_route():
    data = request.get_json()
    defauts = data.get('defauts')
    if not defauts or len(defauts) != 5:
        return jsonify({'error': '5 défauts requis'}), 400
    try:
        chapelet = generer_personnel(defauts)
        return jsonify({'chapelet': chapelet})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/consultation', methods=['POST'])
def consultation():
    data = request.get_json()
    message = data.get('message')
    if not message:
        return jsonify({'error': 'Message requis'}), 400
    # Détection simple
    if any(w in message.lower() for w in ['maîtriser', 'apprendre', 'domaine', 'entretien', 'concept']):
        return jsonify({'redirige': 'expertise', 'message': message})
    else:
        return jsonify({'redirige': 'personnel', 'message': message})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
