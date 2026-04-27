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

# ================= EXPERTISE (7 jours) =================
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

# ================= DÉVELOPPEMENT PERSONNEL (nouveau prompt structuré) =================
def generer_personnel(defauts):
    # Construction du prompt avec les 5 défauts
    prompt = f"""
Tu vas générer un CHAPELET TAZ BOT – DÉVELOPPEMENT PERSONNEL (21 ou 66 jours) pour un utilisateur qui souhaite corriger les 5 défauts suivants :

1. {defauts[0]}
2. {defauts[1]}
3. {defauts[2]}
4. {defauts[3]}
5. {defauts[4]}

Tu dois produire le texte complet du chapelet en suivant EXACTEMENT la structure ci‑dessous.  
À chaque endroit où tu vois `[...]`, tu remplaces par une phrase positive, concise, adaptée au défaut correspondant et au contexte du Mystère.  
Respecte scrupuleusement les titres, les retours à la ligne, et ne rajoute aucun commentaire en dehors du texte du chapelet.

Voici le modèle à générer :

CHAPELET TAZ BOT – 21 ou 66 JOURS 
COMMENT L’UTILISER
. Vous munir d'un chapelet que vous égrènerez pendant vos prières · Chaque jour pendant 21 ou 66 jours, de préférence la même heure : lis ce texte à voix haute ou mentalement, dans l’ordre, sans rien changer. Si vous sautez, recommencez !· Durée : environ 25 minutes.· A un moment calme.· Tu peux imprimer cette page et cocher les jours sur un calendrier.

DÉBUT (Crucifix et premiers grains)
Signe de croix : “Au nom de mon engagement, de ma lucidité et de ma persévérance.”
Crucifix (1er grain) – prière d’ouverture : “Je ne subis plus ma vie. Je deviens l’acteur de chaque heure.”
3 premiers Ave Maria (grains initiaux) :
1er Ave : “[Phrase positive et courte sur le lâcher-prise des errances passées, adaptée au défaut 1]”
2e Ave : “[Phrase positive sur la constance dans l’action, adaptée au défaut 2]”
3e Ave : “[Phrase positive sur le mérite d’un travail stable et d’une fierté retrouvée, adaptée au défaut 3]”
Gloire au Père (après les 3 Ave) : “Je rends grâce à la vie pour ce nouveau départ.”

---
MYSTÈRE 1 – {defauts[0]}
Méditation : [Raconte un souvenir précis où ce défaut a causé un échec ou une frustration. Puis décris, en 3-4 phrases, la nouvelle action positive qui corrige ce défaut. Inspire-toi du style : “Je me vois au matin, allongé, le téléphone à la main… puis je pose le téléphone, me lève d’un bloc, ouvre la fenêtre.”]
Notre Père : “Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes. Je choisis ma lucidité.”
10 × Ave Maria (le même pour tous les mystères) : “[Une seule phrase courte (max 20 mots) qui corrige les 5 défauts à la fois. Elle doit commencer par ‘Je me lève tôt, je range ma vie, je termine ce que je commence, je sors chaque jour, et j’attire un travail prospère.’, mais tu l’adaptes concrètement aux 5 défauts donnés.]”
Gloire au Père : “Je remercie Dieu et l’univers pour ses réalisations dans ma vie et cette transformation profonde.”

---
MYSTÈRE 2 – {defauts[1]}
Méditation : [Visualisation adaptée au défaut 2 – échec lié au désordre ou au manque d’agenda, puis action positive d’organisation et de planification. Style : “Je revois un jour où mon désordre m’a fait rater une échéance. Maintenant, je note trois tâches et je les accomplis.”]
Notre Père : (identique)
10 × Ave Maria : (identique à celui du mystère 1)
Gloire au Père : (identique)

---
MYSTÈRE 3 – {defauts[2]}
Méditation : [Adaptée au défaut 3 – projet abandonné, frustration, puis reprise d’une petite action quotidienne tenue sans exception.]
Notre Père : (identique)
10 × Ave Maria : (identique)
Gloire au Père : (identique)

---
MYSTÈRE 4 – {defauts[3]}
Méditation : [Adaptée au défaut 4 – enfermement, scrolling, puis sortie, marche, rencontre du monde.]
Notre Père : (identique)
10 × Ave Maria : (identique)
Gloire au Père : (identique)

---
MYSTÈRE 5 – {defauts[4]}
Méditation : [Adaptée au défaut 5 – candidatures sans réponse, découragement, puis utilisation du réseau, contact direct, succès, salaire, aide à la famille.]
Notre Père : (identique)
10 × Ave Maria : (identique)
Gloire au Père : (identique)

---
FIN DU CHAPELET (après le 5e mystère)
Salve Regina : “Ô volonté retrouvée, sois ma lumière et ma force.”
Mantra final : “Ce chapelet de 21 ou 66 jours ancre en moi la discipline joyeuse et l’action efficace.”
Signe de croix final : “Au nom de mon engagement, de ma lucidité et de ma persévérance – ainsi soit-il.”

IMPORTANT : 
- Respecte exactement la structure (titres, retours à la ligne, mots des prières).
- Les phrases entre crochets doivent être rédigées en français naturel, sans négation (pas de “ne… pas”).
- La phrase du Ave Maria unique doit être strictement identique dans les 5 mystères.
- Ne rajoute aucun commentaire avant ou après le texte.
"""
    try:
        raw = call_deepseek(prompt, max_tokens=3500)
        contenu = clean_markdown(raw)
        contenu = remove_markdown_chars(contenu)
        return contenu
    except Exception as e:
        fallback = f"CHAPELET TAZ BOT – DÉVELOPPEMENT PERSONNEL (version temporaire)\n\n"
        fallback += f"Défauts :\n1. {defauts[0]}\n2. {defauts[1]}\n3. {defauts[2]}\n4. {defauts[3]}\n5. {defauts[4]}\n\n"
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
