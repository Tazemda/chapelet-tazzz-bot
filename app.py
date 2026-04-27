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

def call_deepseek(prompt, max_tokens=2000):
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
        resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=150)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"API error {resp.status_code}: {resp.text[:200]}")
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

# ================= EXPERTISE =================
PROMPT_JOUR = """
Tu es un expert pédagogique. Domaine : "{domaine}".

Génère le contenu complet du **Jour {jour_num}** sur 7 jours.  
L'objectif général du jour {jour_num} est : {titre_objectif}.

Commence par le titre : `## **JOUR {jour_num} : [TITRE PERTINENT EN MAJUSCULES, ADAPTÉ AU DOMAINE]**`

Puis, EXACTEMENT 5 DIZAINES. Chaque dizaine doit suivre ce format (concis) :

**DIZAINE X : Concept : [nom du concept]**

1) **Méditation synthèse générale en tenant un gros grain** : exactement 7 phrases moyennement denses non numérotés (toutes les méditations, tous les jours) : définition + rôle + exemple court.

2) A la place du **Notre Père**, écrire : RÉPÈTE 3 fois sans égrener le chapelet : une seule phrase, question centrale.

3) A la place du **Je vous salue Marie**, écrire : RÉPÈTE 10 fois en égrenant 10 petits grains: exactement 5 phrases (toutes les méditations, tous les jours) synthétiques, numérotées et mémorisables.

4) A la place du **Gloire au Père**, écrire : RÉPÈTE 3 fois sans égrener: "Le concept [nom] est consolidé."

Soigne la qualité. Ne dépasse pas 2000 tokens au total.
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
        raw = call_deepseek(prompt, max_tokens=2000)
        contenu = clean_markdown(raw)
        contenu = remove_markdown_chars(contenu)
        if not re.search(r'JOUR\s+\d+', contenu, re.IGNORECASE):
            contenu = f"JOUR {jour_num} – {titre_objectif.upper()}\n\n{contenu}"
        return contenu
    except Exception as e:
        print(f"Erreur jour {jour_num}: {e}")
        return f"JOUR {jour_num} – {titre_objectif.upper()} (version de secours)\n\n(erreur technique, veuillez réessayer)"

# ================= DÉVELOPPEMENT PERSONNEL (version avec le gabarit demandé) =================
def generer_personnel(defauts):
    prompt = f"""
Tu vas générer un CHAPELET TAZ BOT – DÉVELOPPEMENT PERSONNEL (21 ou 66 jours).

Les 5 défauts à corriger sont :
1. {defauts[0]}
2. {defauts[1]}
3. {defauts[2]}
4. {defauts[3]}
5. {defauts[4]}

Tu dois produire le texte exactement selon le modèle ci-dessous. Respecte strictement la structure, les titres, les retours à la ligne. Les parties entre crochets [ ] doivent être remplacées par du contenu adapté aux défauts correspondants.

Voici le modèle à suivre :

CHAPELET TAZ BOT – 21 ou 66 JOURS 
COMMENT L’UTILISER
. Vous munir d'un chapelet que vous égrènerez pendant vos prières · Chaque jour pendant 21 ou 66 jours, de préférence la même heure : lis ce texte à voix haute ou mentalement, dans l’ordre, sans rien changer. Si vous sautez, recommencez !· Durée : environ 25 minutes.· A un moment calme.· Tu peux imprimer cette page et cocher les jours sur un calendrier.

DÉBUT (Crucifix et premiers grains)
Signe de croix : “Au nom de mon engagement, de ma lucidité et de ma persévérance.”
Crucifix (1er grain) – prière d’ouverture : “Je ne subis plus ma vie. Je deviens l’acteur de chaque heure.”
3 premiers Ave Maria (grains initiaux) :
1er Ave : “[phrase positive sur le lâcher-prise des errances passées, adaptée au premier défaut]”
2e Ave : “[phrase positive sur la constance, adaptée au second défaut]”
3e Ave : “[phrase positive sur le mérite d’un travail stable, adaptée au troisième défaut]”
Gloire au Père : “Je rends grâce à la vie pour ce nouveau départ.”

---
MYSTÈRE 1 – LE LEVER ET L’ACTION MATINALE
Méditation : [visualisation courte : échec lié au premier défaut, puis réussite positive] (Inspire-toi de : Je me vois au matin, allongé, le téléphone à la main… puis je me lève victorieux.)
Notre Père : “Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes. Je choisis ma lucidité.”
10 × Ave Maria (le même pour tous les mystères) : “[une phrase courte qui corrige les 5 défauts, en commençant par ‘Je me lève tôt, je range ma vie, je termine ce que je commence, je sors chaque jour, et j’attire un travail prospère.’ mais personnalisée]”
Gloire au Père : “Je remercie Dieu et l’univers pour ses réalisations dans ma vie et cette transformation profonde.”

---
MYSTÈRE 2 – L’ORDRE ET L’AGENDA TENU
Méditation : [adaptée au deuxième défaut – désordre, agenda, planification réussie]
Notre Père : idem
10 × Ave Maria : (identique)
Gloire au Père : idem

---
MYSTÈRE 3 – LA CONSTANCE ET LA FINITION DES PROJETS
Méditation : [adaptée au troisième défaut – abandon, petite action quotidienne tenue]
Notre Père : idem
10 × Ave Maria : (identique)
Gloire au Père : idem

---
MYSTÈRE 4 – LA SORTIE ET LA RENCONTRE DU MONDE
Méditation : [adaptée au quatrième défaut – enfermement, scrolling, sortie]
Notre Père : idem
10 × Ave Maria : (identique)
Gloire au Père : idem

---
MYSTÈRE 5 – LA CONFIANCE EN L’EMPLOI ET LA PROSPÉRITÉ
Méditation : [adaptée au cinquième défaut – candidatures, découragement, puis succès]
Notre Père : idem
10 × Ave Maria : (identique)
Gloire au Père : idem

---
FIN DU CHAPELET (après le 5e mystère)
Salve Regina : “Ô volonté retrouvée, sois ma lumière et ma force.”
Mantra final : “Ce chapelet de 21 ou 66 jours ancre en moi la discipline joyeuse et l’action efficace.”
Signe de croix final : “Au nom de mon engagement, de ma lucidité et de ma persévérance – ainsi soit-il.”

IMPORTANT : Ne rajoute aucun commentaire. Remplace TOUS les [texte] par des phrases concrètes, positives, sans négation.
Génère le texte complet maintenant.
"""
    try:
        raw = call_deepseek(prompt, max_tokens=3500)
        contenu = clean_markdown(raw)
        contenu = remove_markdown_chars(contenu)
        return contenu
    except Exception as e:
        fallback = f"CHAPELET TAZ BOT – DÉVELOPPEMENT PERSONNEL (version temporaire)\n\n"
        fallback += f"Défauts : {', '.join(defauts)}\n\n"
        fallback += f"Erreur API : {str(e)}. Vérifiez votre solde DeepSeek.\n"
        return fallback

# ================= ROUTES =================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generer_jour_expertise', methods=['POST'])
def generer_jour_expertise_route():
    data = request.get_json()
    domaine = data.get('domaine')
    jour = data.get('jour')
    if not domaine or not jour:
        return jsonify({'error': 'Domaine et jour requis'}), 400
    contenu = generer_jour_expertise(domaine, int(jour))
    return jsonify({'contenu': contenu})

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
