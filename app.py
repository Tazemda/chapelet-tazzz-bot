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

def call_deepseek(prompt, max_tokens=3000):
    if not DEEPSEEK_API_KEY:
        raise Exception("Clé API manquante")
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": max_tokens
    }
    try:
        resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=180)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"API error {resp.status_code}: {resp.text[:500]}")
    except requests.exceptions.Timeout:
        raise Exception("L'API DeepSeek a mis trop de temps à répondre. Réessayez.")
    except Exception as e:
        raise Exception(f"Erreur API: {str(e)}")

def clean_markdown(text):
    text = re.sub(r'```[\s\S]*?```', '', text)
    return text.replace('`', '').strip()

def remove_markdown_chars(text):
    text = re.sub(r'\*\*', '', text)
    text = re.sub(r'\*', '', text)
    text = re.sub(r'#', '', text)
    return text

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

# ================= EXPERTISE CLASSIQUE (7 jours) =================
PROMPT_JOUR = """
Tu es un expert pédagogique. Domaine : "{domaine}".

Génère le contenu complet du **Jour {jour_num}** sur 7 jours.  
L'objectif général du jour {jour_num} est : {titre_objectif}.

Commence par le titre : `## **JOUR {jour_num} : [TITRE PERTINENT EN MAJUSCULES, ADAPTÉ AU DOMAINE]**`

Puis, EXACTEMENT 5 DIZAINES. Chaque dizaine doit suivre ce format (concis) :

**DIZAINE X : CONCEPT : [nom du concept]**

A) **Synthèse générale Méditation à lire en tenant un gros grain du chapelet** : exactement 8 phrases moyennement denses non numérotés (toutes les méditations, tous les jours) : définition + rôle + exemple court.

B) A la place du **Notre Père**, écrire : RÉPÈTE 3 fois sans égrener le chapelet : une seule phrase, question centrale.

C) A la place du **Je vous salue Marie**, écrire : RÉPÈTE 10 fois en égrenant 10 petits grains: exactement 6 phrases (toutes les méditations, tous les jours) synthétiques, numérotées et mémorisables.

D) A la place du **Gloire au Père**, écrire : RÉPÈTE 3 fois sans égrener: "Le concept [nom] est consolidé."

(même structure pour DIZAINE 2 à 5)

Soigne la qualité. Ne dépasse pas 2500 tokens au total.
"""

def generer_jour_expertise(domaine, jour_num):
    objectifs = [
        "Découverte des bases fondamentales",
        "Approfondissement des pratiques clés",
        "Cas complexes et exceptions",
        "Contrôle qualité et indicateurs",
        "Gestion des risques et plan d'action",
        "Synthèse et liens entre concepts",
        "Auto‑évaluation et perfectionnement"
    ]
    titre_objectif = objectifs[jour_num-1]
    prompt = PROMPT_JOUR.format(domaine=domaine, jour_num=jour_num, titre_objectif=titre_objectif)
    try:
        raw = call_deepseek(prompt, max_tokens=3000)
        contenu = clean_markdown(raw)
        contenu = remove_markdown_chars(contenu)
        if not re.search(r'JOUR\s+\d+', contenu, re.IGNORECASE):
            contenu = f"JOUR {jour_num} – {titre_objectif.upper()}\n\n{contenu}"
        return contenu
    except Exception as e:
        print(f"Erreur jour {jour_num}: {e}")
        return f"JOUR {jour_num} – {titre_objectif.upper()} (version de secours)\n\n(erreur technique: {str(e)})"

# ================= COURS (6 CHAPITRES) =================
PROMPT_CHAPITRE_JOUR = """
Tu es un expert pédagogique. Tu reçois le texte d'un chapitre.
Transforme ce chapitre en contenu structuré pour une journée d'étude (5 dizaines).

Voici le texte du chapitre :

{texte_chapitre}

Génère le contenu du **Jour {jour_num}** (5 dizaines) selon le format exact suivant :

## **JOUR {jour_num} : [TITRE ADAPTÉ AU CHAPITRE]**

**DIZAINE 1 : CONCEPT : [nom]**
A) **Méditation** : 8 phrases (définition, rôle, exemple court).
B) **Notre Père** : une question centrale (RÉPÈTE 3 fois).
C) **Je vous salue Marie** : 6 phrases numérotées (RÉPÈTE 10 fois).
D) **Gloire au Père** : "Le concept [nom] est consolidé." (RÉPÈTE 3 fois)

(même structure pour DIZAINE 2 à 5)

Soigne la qualité, reste fidèle au texte source. Ne dépasse pas 2800 tokens.
"""

@app.route('/generer_chapitre', methods=['POST'])
def generer_chapitre_route():
    try:
        data = request.get_json()
        texte = data.get('texte')
        num = data.get('num')
        if not texte or not num:
            return jsonify({'error': 'Texte et numéro requis'}), 400
        prompt = PROMPT_CHAPITRE_JOUR.format(texte_chapitre=texte, jour_num=num)
        contenu = call_deepseek(prompt, max_tokens=3000)
        contenu = clean_markdown(contenu)
        contenu = remove_markdown_chars(contenu)
        return jsonify({'contenu': contenu})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ================= ENTRETIEN (4 jours) =================
PROMPT_ENTRETIEN = """
Tu es un coach expert en préparation aux entretiens d'embauche.

Le candidat fournit son CV et une offre d'emploi.  
Génère un programme personnalisé de **4 jours** (5 dizaines par jour) selon le plan suivant :

### JOUR 1 – Entretien RH (motivation, comportement, pitch)
Dizaine 1 – Analyse CV+Offre : matching compétences, écarts, forces.
Dizaine 2 – Pitch personnalisé : 30-60 secondes, version améliorable.
Dizaine 3 – Questions RH fréquentes : 5 questions + réponses structurées.
Dizaine 4 – Méthode STAR (soft skills) : Situation, Tâche, Action, Résultat.
Dizaine 5 – Banque de phrases pro : amélioration du langage, reformulation.

### JOUR 2 – Entretien technique (compétences, mises en situation)
Dizaine 1 – Extraction compétences techniques + matching avec offre.
Dizaine 2 – Questions techniques ciblées : 5 questions + réponses.
Dizaine 3 – Étude de cas réaliste : problème concret du métier.
Dizaine 4 – STAR technique (projets) : explication chiffrée des réalisations.
Dizaine 5 – Révisions & améliorations techniques.

### JOUR 3 – Entretien final + négociation (motivation avancée, clôture)
Dizaine 1 – Points forts / points faibles : 3 forces, 1 axe de progression.
Dizaine 2 – Questions difficiles : “Pourquoi vous ?”, “Pourquoi pas vous ?”…
Dizaine 3 – Argumentaire de vente : script de pitch final.
Dizaine 4 – Négociation (salaire, avantages) : fourchette + arguments.
Dizaine 5 – Questions au recruteur : 3-5 questions intelligentes.

### JOUR 4 – Simulation réaliste (avec questions dynamiques)
Dizaine 1 – Questions RH simulation (motivation, pitch)
Dizaine 2 – Questions techniques simulation
Dizaine 3 – Questions comportementales STAR simulation
Dizaine 4 – Objections & négociation simulation
Dizaine 5 – Bilan : score global (sur 20), points forts, axes d’amélioration, conseils.

Chaque dizaine doit suivre le format :

**DIZAINE X : [titre]**
A) **Méditation** : 8 phrases (définition, importance en entretien, exemple concret issu du CV ou de l’offre).
B) **Notre Père** : une question centrale (RÉPÈTE 3 fois).
C) **Je vous salue Marie** : 6 phrases numérotées (RÉPÈTE 10 fois) – conseils pratiques, exemples.
D) **Gloire au Père** : "Le concept [titre] est consolidé." (RÉPÈTE 3 fois)

Soigne la personnalisation : utilise le CV et l’offre pour adapter chaque exemple.  
Ne dépasse pas 3500 tokens au total.
"""

@app.route('/generer_entretien', methods=['POST'])
def generer_entretien_route():
    try:
        data = request.get_json()
        cv = data.get('cv')
        offre = data.get('offre')
        if not cv or not offre:
            return jsonify({'error': 'CV et offre requis'}), 400
        prompt = PROMPT_ENTRETIEN.format(cv=cv, offre=offre)
        contenu = call_deepseek(prompt, max_tokens=3500)
        contenu = clean_markdown(contenu)
        contenu = remove_markdown_chars(contenu)
        # Découper le contenu en 4 jours (on suppose que l'API génère les 4 jours à la suite)
        # Pour simplifier, on retourne le texte complet ; l'interface le découpera (on peut aussi découper ici)
        return jsonify({'contenu': contenu})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ================= ROUTES COMMUNES =================
@app.route('/generer_jour_expertise', methods=['POST'])
def generer_jour_expertise_route():
    try:
        data = request.get_json()
        domaine = data.get('domaine')
        jour = data.get('jour')
        if not domaine or not jour:
            return jsonify({'error': 'Domaine et jour requis'}), 400
        contenu = generer_jour_expertise(domaine, int(jour))
        return jsonify({'contenu': contenu})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
