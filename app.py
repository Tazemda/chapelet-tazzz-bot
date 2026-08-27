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

# -------------------------------------------------------------------
# Gestion de l'API DeepSeek
# -------------------------------------------------------------------
def call_deepseek(prompt, max_tokens=2000, temperature=0.7):
    """Appelle l'API DeepSeek et retourne le texte généré."""
    if not DEEPSEEK_API_KEY:
        raise Exception("Clé API DeepSeek manquante dans les variables d'environnement.")
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
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
    except requests.exceptions.ConnectionError:
        raise Exception("Impossible de se connecter à l'API DeepSeek. Vérifiez votre connexion.")
    except Exception as e:
        raise Exception(f"Erreur API: {str(e)}")

# -------------------------------------------------------------------
# Nettoyage du markdown généré
# -------------------------------------------------------------------
def clean_markdown(text):
    """Supprime les blocs de code markdown et les backticks."""
    # Supprime les éventuels ``` ... ```
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Supprime les backticks simples
    text = text.replace('`', '')
    return text.strip()

def remove_markdown_chars(text):
    """Retire les caractères markdown de base pour un affichage propre."""
    # Supprime les astérisques de mise en gras / italique
    text = re.sub(r'\*\*', '', text)
    text = re.sub(r'\*', '', text)
    # Supprime les dièses de titre
    text = re.sub(r'#', '', text)
    # Supprime les underscores
    text = re.sub(r'_', '', text)
    # Supprime les liens [texte](url) -> texte
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    return text

# -------------------------------------------------------------------
# Base de données pour feedback
# -------------------------------------------------------------------
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

# ===================================================================
# PROMPTS
# ===================================================================

# ---------- Expertise en 7 jours ----------
PROMPT_JOUR_EXPERTISE = """
Tu es un expert pédagogique. Domaine : "{domaine}".
Génère le contenu complet du Jour {jour_num} sur 7 jours.
L'objectif général du jour {jour_num} est : {titre_objectif}.

Commence par le titre exact : ## **JOUR {jour_num} : [TITRE PERTINENT EN MAJUSCULES, ADAPTÉ AU DOMAINE]**

Ensuite, EXACTEMENT 5 DIZAINES. Chaque dizaine doit suivre ce format (concis et mémorisable) :

DIZAINE X : CONCEPT : [nom du concept en majuscules]
A) Synthèse générale Méditation à lire en tenant un gros grain du chapelet : exactement 8 phrases moyennement denses non numérotées (toutes les méditations, tous les jours) : définition + rôle + exemple court.
B) À la place du Notre Père, écrire : RÉPÈTE 3 fois sans égrener le chapelet : une seule phrase, question centrale.
C) À la place du Je vous salue Marie, écrire : RÉPÈTE 10 fois en égrenant 10 petits grains : exactement 6 phrases (toutes les méditations, tous les jours) synthétiques, numérotées de 1 à 6 et mémorisables.
D) À la place du Gloire au Père, écrire : RÉPÈTE 3 fois sans égrener : "Le concept [nom] est consolidé."

(Même structure pour DIZAINE 2 à 5)

Soigne la qualité, sois précis et adapté au domaine. Ne dépasse pas 2500 tokens au total.
"""

# ---------- Cours (6 chapitres -> 6 jours) ----------
PROMPT_CHAPITRE_JOUR = """
Tu es un expert pédagogique. Tu reçois le texte d'un chapitre.
Transforme ce chapitre en contenu structuré pour une journée d'étude (5 dizaines).

Voici le texte du chapitre :
{texte_chapitre}

Génère le contenu du Jour {jour_num} (5 dizaines) selon le format exact suivant :

JOUR {jour_num} : [TITRE ADAPTÉ AU CHAPITRE]

DIZAINE 1 : CONCEPT : [nom]
A) Méditation : 8 phrases (définition, rôle, exemple court).
B) Notre Père : une question centrale (RÉPÈTE 3 fois).
C) Je vous salue Marie : 6 phrases numérotées (RÉPÈTE 10 fois).
D) Gloire au Père : "Le concept [nom] est consolidé." (RÉPÈTE 3 fois)

(Même structure pour DIZAINE 2 à 5)

Soigne la qualité, reste fidèle au texte source, et ne dépasse pas 2800 tokens.
"""

# ---------- Entretien d'embauche (3 jours + simulation) ----------
PROMPT_ENTRETIEN_DIZAINE = """
Tu es le Dr Tazzz, expert en préparation aux entretiens d'embauche.
CV du candidat : {cv}
Offre d'emploi : {offre}

Génère le contenu de la DIZAINE {dizaine_num} du JOUR {jour_num} en suivant EXACTEMENT le plan ci-dessous.
N'utilise aucun terme religieux (pas de "Notre Père", "Je vous salue Marie", "Gloire"). Utilise uniquement les notations I., II., III.

JOUR 1 – Entretien RH (objectif : convaincre humainement, motivation, comportement, pitch)
Dizaine 1 – Analyse CV + offre
I. Matching compétences (alignements et forces)
II. Écarts (faiblesses par rapport à l’offre)
III. Atout majeur qui rend le candidat spécial
Dizaine 2 – Présentation et pitch
I. Conseil du Dr Tazzz sur la forme et le fond de la présentation au RH
II. Pitch personnalisé (30-60 secondes) que le candidat peut répéter
Dizaine 3 – Questions RH (partie 1)
3 questions RH fréquentes (parmi : ouverture, motivation, situationnelles, compétences, comportementales, clôture)
Chaque question : réponse personnalisée avec méthode STAR (Situation, Tâche, Action, Résultat)
Dizaine 4 – Questions RH (partie 2)
3 autres questions RH (autres types)
Chaque question avec réponse STAR personnalisée
Dizaine 5 – Banque de phrases
Une série de 10 phrases professionnelles à répéter (phrases types pour parler de soi, de ses compétences, de sa motivation)

JOUR 2 – Entretien technique (objectif : prouver ses compétences)
Dizaine 1 – Analyse technique
I. Matching compétences techniques (alignements)
II. Écarts techniques (compétences manquantes)
III. Atout technique majeur du candidat
Dizaine 2 – Conseils pour l’entretien technique
I. Conseil du Dr Tazzz sur la façon de s’entretenir avec l’expert technique (différences avec le RH, langage, robustesse)
Dizaine 3 – Questions techniques (partie 1)
3 questions techniques fréquentes (type : ouverture, compétences, situationnelles)
Chaque question avec réponse STAR adaptée au CV et à l’offre
Dizaine 4 – Questions techniques (partie 2)
3 autres questions techniques (compétences avancées, étude de cas, clôture)
Chaque question avec réponse STAR technique + explication de projets chiffrés
Dizaine 5 – Banque de phrases techniques
10 phrases professionnelles à répéter pour l’entretien avec le supérieur hiérarchique

JOUR 3 – Entretien final + négociation (objectif : motivation avancée, clôture)
Dizaine 1 – Points forts / points faibles
I. 3 forces majeures du candidat
II. 1 axe de progression (point faible, présenté de manière constructive)
Dizaine 2 – Questions difficiles
I. “Pourquoi vous ?” – réponse argumentée
II. “Pourquoi pas vous ?” – gestion des objections
Dizaine 3 – Argumentaire de vente
Script personnalisé de pitch final (30-60 secondes) pour convaincre le recruteur
Dizaine 4 – Négociation (salaire, avantages)
I. Fourchette de salaire cohérente avec le poste et le CV
II. Arguments pour justifier la prétention salariale
III. Autres avantages à négocier (formation, télétravail, etc.)
Dizaine 5 – Questions au recruteur
5 questions intelligentes que le candidat peut poser en fin d’entretien

IMPORTANT :
    • Rédige de manière personnalisée (utilise le CV et l’offre).
    • Pour les réponses STAR, donne un exemple concret tiré du CV (projet, expérience).
    • Ne dépasse pas 1000 tokens par dizaine.
    • Ne mets aucun titre religieux.
"""

# ===================================================================
# ROUTES BACKEND
# ===================================================================

@app.route('/')
def index():
    return render_template('index.html')

# ---------- Génération Expertise (un jour complet) ----------
@app.route('/generer_jour_expertise', methods=['POST'])
def generer_jour_expertise_route():
    try:
        data = request.get_json()
        domaine = data.get('domaine')
        jour = int(data.get('jour'))
        if not domaine or not jour:
            return jsonify({'error': 'Domaine et jour requis'}), 400

        objectifs = [
            "Découverte des bases fondamentales",
            "Approfondissement des pratiques clés",
            "Cas complexes et exceptions",
            "Contrôle qualité et indicateurs",
            "Gestion des risques et plan d'action",
            "Synthèse et liens entre concepts",
            "Auto‑évaluation et perfectionnement"
        ]
        titre_objectif = objectifs[jour-1]

        prompt = PROMPT_JOUR_EXPERTISE.format(
            domaine=domaine,
            jour_num=jour,
            titre_objectif=titre_objectif
        )
        raw = call_deepseek(prompt, max_tokens=3000)
        contenu = clean_markdown(raw)
        contenu = remove_markdown_chars(contenu)
        # Vérification basique que le jour est bien mentionné
        if not re.search(r'JOUR\s+' + str(jour), contenu, re.IGNORECASE):
            contenu = f"JOUR {jour} – {titre_objectif.upper()}\n\n{contenu}"
        return jsonify({'contenu': contenu})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------- Génération Cours (un chapitre -> un jour) ----------
@app.route('/generer_chapitre', methods=['POST'])
def generer_chapitre_route():
    try:
        data = request.get_json()
        texte = data.get('texte')
        num = int(data.get('num'))
        if not texte or not num:
            return jsonify({'error': 'Texte et numéro requis'}), 400

        prompt = PROMPT_CHAPITRE_JOUR.format(texte_chapitre=texte, jour_num=num)
        raw = call_deepseek(prompt, max_tokens=3000)
        contenu = clean_markdown(raw)
        contenu = remove_markdown_chars(contenu)
        return jsonify({'contenu': contenu})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------- Génération Entretien (une dizaine) ----------
@app.route('/generer_dizaine_entretien', methods=['POST'])
def generer_dizaine_entretien_route():
    try:
        data = request.get_json()
        cv = data.get('cv')
        offre = data.get('offre')
        jour = int(data.get('jour'))
        dizaine = int(data.get('dizaine'))
        if not cv or not offre or not jour or not dizaine:
            return jsonify({'error': 'CV, offre, jour et dizaine requis'}), 400

        prompt = PROMPT_ENTRETIEN_DIZAINE.format(
            cv=cv,
            offre=offre,
            jour_num=jour,
            dizaine_num=dizaine
        )
        raw = call_deepseek(prompt, max_tokens=1000)
        contenu = clean_markdown(raw)
        contenu = remove_markdown_chars(contenu)
        return jsonify({'contenu': contenu})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------- Feedback ----------
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
