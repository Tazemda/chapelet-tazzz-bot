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

**DIZAINE X : CONCEPT : [nom du concept]**

A) **Méditation synthèse générale, en tenant un gros grain du chapelet** : exactement 10 phrases moyennement denses non numérotés (toutes les méditations, tous les jours) : définition + rôle + exemple court.

B) A la place du **Notre Père**, écrire : RÉPÈTE 3 fois sans égrener le chapelet : une seule phrase, question centrale.

C) A la place du **Je vous salue Marie**, écrire : RÉPÈTE 10 fois en égrenant 10 petits grains: exactement 7 phrases (toutes les méditations, tous les jours) synthétiques, numérotées et mémorisables.

D) A la place du **Gloire au Père**, écrire : RÉPÈTE 3 fois sans égrener: "Le concept [nom] est consolidé."

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

# ================= DÉVELOPPEMENT PERSONNEL (NOUVEAU PROMPT STRUCTURÉ 21 JOURS) =================
def generer_personnel(defauts):
    # Construction du prompt exact selon la structure fixe du chapelet 21 jours
    prompt = f"""
Tu vas générer un CHAPELET TAZ BOT – DÉVELOPPEMENT PERSONNEL (21 jours) pour un utilisateur qui souhaite corriger les 5 défauts suivants.  
Les défauts sont donnés par l’utilisateur. Remplace chaque `{{défaut_X}}` par le libellé exact du défaut correspondant.

Défaut 1 : {defauts[0]}  
Défaut 2 : {defauts[1]}  
Défaut 3 : {defauts[2]}  
Défaut 4 : {defauts[3]}  
Défaut 5 : {defauts[4]}

Tu dois produire le texte complet du chapelet en suivant EXACTEMENT la structure ci-dessous.  
Ne rajoute aucun commentaire, aucun titre supplémentaire. Respecte scrupuleusement les retours à la ligne, les guillemets, et le contenu des prières (seules les parties entre crochets sont à adapter).

---

📿 CHAPELET TAZ BOT – 21 JOURS (STRUCTURE FIXE)

DÉBUT (Crucifix et premiers grains)

Signe de croix :  
“Au nom de mon engagement, de ma lucidité et de ma persévérance.”

Crucifix (1 grain) – mantra d’ouverture :  
“Je ne subis plus ma vie. Je deviens l’acteur de chaque heure.”

3 premiers Ave Maria (grains initiaux) :  
1er Ave : “Je laisse derrière moi le poids des errances passées, en particulier quand [{defauts[0]}] me freinait.”  
2e Ave : “Je choisis la constance dans l’action, même face à [{defauts[1]}].”  
3e Ave : “Je mérite un travail stable, une fierté retrouvée, malgré [{defauts[2]}].”

Gloire au Père (après les 3 Ave) :  
“Je rends grâce à la vie pour ce nouveau départ.”

---

MYSTÈRE 1 – LE LEVER ET L’ACTION MATINALE

Méditation :  
Je me vois au matin, allongé, le téléphone à la main. Je ressens la lourdeur, les heures qui glissent. Puis je me vois poser le téléphone, me lever d’un bloc, ouvrir la fenêtre. Mon corps obéit. Je choisis ce lever victorieux. (Adapté au défaut 1 : {defauts[0]})

Notre Père :  
“Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes. Je choisis ma lucidité.”

10 × Ave Maria (le même pour tous les mystères) :  
“Je me lève tôt, je range ma vie, je termine ce que je commence, je sors chaque jour, et j’attire un travail prospère.”

Gloire au Père :  
“Je remercie Dieu et l’univers pour cette transformation profonde.”

---

MYSTÈRE 2 – L’ORDRE ET L’AGENDA TENU

Méditation :  
Je revois un jour où mon désordre m’a fait rater une échéance. La honte, la perte de temps. Maintenant, je me vois assis calmement, mon agenda ouvert, je note trois tâches pour demain. Je coche au fur et à mesure. À la fin de la journée, tout est accompli ou reporté en pleine conscience. (Adapté au défaut 2 : {defauts[1]})

Notre Père :  
“Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes. Je choisis ma lucidité.”

10 × Ave Maria (identique) :  
“Je me lève tôt, je range ma vie, je termine ce que je commence, je sors chaque jour, et j’attire un travail prospère.”

Gloire au Père :  
“Je remercie Dieu et l’univers pour cette transformation profonde.”

---

MYSTÈRE 3 – LA CONSTANCE ET LA FINITION DES PROJETS

Méditation :  
Je me souviens d’un projet abandonné (master, sport, concours). La frustration de l’inachevé. Maintenant, je me vois reprendre une toute petite action, chaque jour, sans exception. Je tiens. La régularité devient ma force. (Adapté au défaut 3 : {defauts[2]})

Notre Père :  
“Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes. Je choisis ma lucidité.”

10 × Ave Maria (identique) :  
“Je me lève tôt, je range ma vie, je termine ce que je commence, je sors chaque jour, et j’attire un travail prospère.”

Gloire au Père :  
“Je remercie Dieu et l’univers pour cette transformation profonde.”

---

MYSTÈRE 4 – LA SORTIE ET LA RENCONTRE DU MONDE

Méditation :  
Je me vois enfermé, dormant, scrollant, alors que dehors la vie continue. Je ressens l’étouffement. Puis je me vois franchir la porte, respirer l’air, marcher, croiser des regards. Je suis vivant et connecté. (Adapté au défaut 4 : {defauts[3]})

Notre Père :  
“Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes. Je choisis ma lucidité.”

10 × Ave Maria (identique) :  
“Je me lève tôt, je range ma vie, je termine ce que je commence, je sors chaque jour, et j’attire un travail prospère.”

Gloire au Père :  
“Je remercie Dieu et l’univers pour cette transformation profonde.”

---

MYSTÈRE 5 – LA CONFIANCE EN L’EMPLOI ET LA PROSPÉRITÉ

Méditation :  
Je revois ces centaines de candidatures sans réponse. Le découragement. Maintenant, je me vois utiliser mon réseau, contacter directement, valoriser mes compétences. Je reçois une réponse positive. Un salaire arrive. J’envoie de l’argent à ma famille. Je rembourse mes dettes. (Adapté au défaut 5 : {defauts[4]})

Notre Père :  
“Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes. Je choisis ma lucidité.”

10 × Ave Maria (identique) :  
“Je me lève tôt, je range ma vie, je termine ce que je commence, je sors chaque jour, et j’attire un travail prospère.”

Gloire au Père :  
“Je remercie Dieu et l’univers pour cette transformation profonde.”

---

FIN DU CHAPELET (après le 5e mystère)

Salve Regina :  
“Ô volonté retrouvée, sois ma lumière et ma force.”

Mantra final :  
“Ce chapelet de 21 jours ancre en moi la discipline joyeuse et l’action efficace.”

Signe de croix final :  
“Au nom de mon engagement, de ma lucidité et de ma persévérance – ainsi soit-il.”

---

IMPORTANT :  
- N’ajoute aucun texte avant ou après ce contenu.  
- Remplace les `{defauts[0]}` etc. par les vrais libellés.  
- Respecte l’orthographe, les guillemets et les sauts de ligne exacts.
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
