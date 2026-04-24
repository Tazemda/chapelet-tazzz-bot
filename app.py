import os
import re
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tazbot-secret-key")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

def call_deepseek(prompt, max_tokens=2500):
    if not DEEPSEEK_API_KEY:
        raise Exception("Clé API DeepSeek manquante")
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": max_tokens
    }
    try:
        resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=120)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"API error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        raise Exception(f"Erreur appel API: {str(e)}")

def clean_markdown(text):
    text = re.sub(r'```[\s\S]*?```', '', text)
    return text.replace('`', '').strip()

def init_db():
    conn = sqlite3.connect('tazbot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS feedback
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT,
                  note INTEGER,
                  commentaire TEXT)''')
    conn.commit()
    conn.close()
init_db()

def generer_jour(domaine, jour_num):
    # Objectifs neutres (sans référence au médicament)
    objectifs = [
        "Découverte des bases fondamentales",
        "Approfondissement des pratiques clés",
        "Cas complexes et exceptions",
        "Contrôle qualité et indicateurs",
        "Gestion des risques et plan d'action",
        "Synthèse et liens entre concepts",
        "Auto‑évaluation et perfectionnement"
    ]
    titre_jour = objectifs[jour_num-1]
    prompt = f"""
Génère le contenu du **Jour {jour_num}** d'un chapelet d'apprentissage sur le domaine : "{domaine}".
Objectif de ce jour : {titre_jour}.

Pour ce jour, invente **5 concepts** (DIZAINE 1 à 5). Pour chaque concept, écris exactement ce format :

**DIZAINE X – Concept : [nom du concept]**

**1) Méditation (grande fiche)**  
*Instruction : Tenez le gros grain. Lisez ce paragraphe comme une fiche de cours.*  
(Paragraphe dense : définitions, exemples, points clés.)

**2) Notre Père**  
*Récitez cette question 3 fois.*  
« Question problématique sur le concept »

**3) Je vous salue Marie**  
*Répétez ce paragraphe 10 fois (5 lectures, 5 sans regarder).*  
(Paragraphe synthétique de plusieurs phrases.)

**4) Gloire au Père**  
*Récitez cette phrase 3 fois.*  
« Le concept "[nom]" est connu et consolidé. »

Le contenu doit être adapté au domaine "{domaine}". Commence directement par "**DIZAINE 1**". N'ajoute pas de titre général avant.
"""
    raw = call_deepseek(prompt, max_tokens=2500)
    raw = clean_markdown(raw)
    return f"--- Jour {jour_num} – {titre_jour} ---\n\n{raw}"

def generer_personnel(defauts):
    mantra = "Je me lève tôt, je termine ce que je commence, je sors chaque jour, je structure ma vie, j'attire un travail stable."
    texte = f"""
**CHAPELET TAZZZ BOT – MODE DÉVELOPPEMENT PERSONNEL (21/66 jours)**

> *Munissez-vous d'un chapelet pour égrener chaque grain...*

### DÉBUT
- Signe de croix : "Au nom de mon engagement, de ma lucidité et de ma persévérance."
- Crucifix : "Je ne subis plus ma vie. Je deviens l'acteur de chaque heure."
- 3 Ave initiaux : "Je laisse derrière moi le poids des errances passées." / "Je choisis la constance..." / "Je mérite un travail stable."
- Gloire : "Je rends grâce pour ce nouveau départ."

### 5 MYSTÈRES
"""
    for i, d in enumerate(defauts, 1):
        texte += f"""
**Mystère {i} – {d}**  
**Méditation** : (souvenir d’un échec passé) … Aujourd’hui, visualisation du comportement opposé réussi.  
**Notre Père** (×3) : "Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention."  
**Je vous salue Marie** (×10) : {mantra}  
**Gloire au Père** (×3) : "Je remercie Dieu et l'univers pour cette transformation."
"""
    texte += """
### FIN
- Salve Regina : "Ô volonté retrouvée, sois ma lumière."
- Mantra final : "Ce chapelet ancre la discipline joyeuse."
- Signe de croix final.

Chapelet Tazzz Bot – © Dr Tazemda
"""
    return texte

# ---------- Routes ----------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generer_jour', methods=['POST'])
def generer_jour_route():
    data = request.get_json()
    domaine = data.get('domaine')
    jour = data.get('jour')
    if not domaine or not jour:
        return jsonify({'error': 'Domaine et jour requis'}), 400
    try:
        contenu = generer_jour(domaine, int(jour))
        return jsonify({'contenu': contenu})
    except Exception as e:
        print(f"Erreur jour {jour}:", e)
        return jsonify({'error': str(e)}), 500

@app.route('/generer_personnel', methods=['POST'])
def generer_personnel_route():
    data = request.get_json()
    defauts = data.get('defauts')
    if not defauts or len(defauts) != 5:
        return jsonify({'error': '5 défauts requis'}), 400
    contenu = generer_personnel(defauts)
    return jsonify({'contenu': contenu})

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
