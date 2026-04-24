import os
import sqlite3
import re
from datetime import datetime
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tazbot-secret-key")

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

# ------------------ GÉNÉRATION EXPERTISE (locale, riche) ------------------
def generer_dizaine(num, concept, meditation, question, ave):
    return f"""
**DIZAINE {num} – Concept : {concept}**

**1) Méditation (grande fiche)**  
*Instruction : Tenez le gros grain. Lisez ce paragraphe lentement, comme une fiche de cours. Vous pouvez aussi le relire plusieurs fois, revoir vos notes personnelles ou consulter d’autres sources.*  
{meditation}

**2) Notre Père**  
*Récitez cette question 3 fois (à voix haute ou mentalement).*  
« {question} »

**3) Je vous salue Marie**  
*Répétez ce paragraphe 10 fois (5 fois en lecture et 5 fois sans regarder). Lisez‑le d’abord pour bien l’ancrer.*  
{ave}

**4) Gloire au Père**  
*Récitez cette phrase 3 fois.*  
« Le concept “{concept}” est connu et consolidé. »
"""

def generer_chapelet_expertise(domaine):
    """Génère un chapelet d'expertise complet sur 7 jours, adapté au domaine."""
    sujet = domaine.strip()
    jours_titres = [
        "Découverte des bases",
        "Approfondissement opérationnel",
        "Cas complexes et exceptions",
        "Contrôle qualité et indicateurs",
        "Gestion des risques et plan d'action",
        "Synthèse et liens entre concepts",
        "Auto‑évaluation et perfectionnement"
    ]
    # Contenu enrichi et personnalisable
    meditations = {
        1: f"La maîtrise de {sujet} commence par une compréhension claire de ses objectifs et de son périmètre. Exemple : dans {sujet}, il est essentiel de connaître les réglementations, les bonnes pratiques et les erreurs courantes. Une formation solide repose sur l'acquisition progressive des concepts fondamentaux.",
        2: f"Les principes fondamentaux de {sujet} incluent la rigueur, la traçabilité et l'amélioration continue. Concrètement, cela signifie qu'il faut documenter chaque action, vérifier régulièrement les résultats et ajuster ses méthodes en fonction des retours d'expérience.",
        3: f"La méthodologie recommandée pour {sujet} se décompose en 4 étapes : analyse préalable, planification, exécution, évaluation. Par exemple, avant d'intervenir, on réalise un diagnostic; ensuite on planifie les tâches; on les réalise en suivant le plan; enfin on mesure les résultats et on corrige.",
        4: f"Les outils essentiels pour {sujet} sont les checklists, les grilles d'observation, les logiciels de suivi et les fiches de contrôle. Exemple : une checklist des points de contrôle permet de ne rien oublier lors d'une intervention.",
        5: f"Pour mesurer la progression en {sujet}, on utilise des indicateurs quantitatifs (nombre d'actions réalisées, taux de conformité) et qualitatifs (satisfaction, qualité perçue). Un bon indicateur est simple, précis et facile à collecter."
    }
    questions = {
        1: f"Quels sont les trois aspects les plus importants à connaître pour bien débuter en {sujet} ?",
        2: f"Comment appliquer les principes de rigueur et de traçabilité dans votre quotidien professionnel ?",
        3: f"Quelles sont les quatre étapes clés de la méthodologie, et comment les enchaîner sans en oublier ?",
        4: f"Quels outils devez-vous maîtriser en priorité pour gagner en efficacité ?",
        5: f"Quels indicateurs vous permettent de suivre vos progrès et d'ajuster votre action ?"
    }
    aves = {
        1: f"Pour maîtriser {sujet}, je commence par en apprendre les définitions et les enjeux. Je retiens que les trois piliers sont : la connaissance théorique, les bonnes pratiques et le retour d'expérience. Je répète ces bases chaque jour pour les ancrer.",
        2: f"Les principes fondamentaux sont : rigueur (suivre les règles), traçabilité (garder des preuves), amélioration continue (corriger après chaque erreur). Je les applique consciemment dans chaque tâche.",
        3: f"La méthode en quatre temps : 1) analyser la situation, 2) planifier les actions, 3) réaliser en suivant le plan, 4) évaluer et ajuster. Je répète ces étapes jusqu'à ce qu'elles deviennent automatiques.",
        4: f"Les outils essentiels sont la checklist, le tableau de bord et la fiche de contrôle. Je m'entraîne à les utiliser sur des cas concrets jusqu'à en maîtriser chaque détail.",
        5: f"Je choisis trois indicateurs pertinents pour mon activité : le taux de réalisation, le nombre d'écarts corrigés, la satisfaction des parties prenantes. Je les relève chaque semaine."
    }
    noms_concepts = [
        f"Fondamentaux de {sujet}",
        f"Principes clés de {sujet}",
        f"Méthodologie pour {sujet}",
        f"Outils essentiels pour {sujet}",
        f"Indicateurs de succès en {sujet}"
    ]
    
    texte = f"""
--- CHAPELET TAZZZ BOT – EXPERTISE (7 jours) ---

Domaine : {sujet}

Ce chapelet est un outil de mémorisation active par répétition rythmée, basé sur la plasticité cérébrale. Tenez un vrai chapelet dans la main.

**Point d’entrée du problème** : Comment maîtriser {sujet} avec rigueur et efficacité ?

**Règle d’or** : Une pratique quotidienne et une visualisation active.

"""
    for jour in range(1, 8):
        texte += f"\n\n--- Jour {jour} – {jours_titres[jour-1]} ---\n"
        for i in range(1, 6):
            texte += generer_dizaine(i, noms_concepts[i-1], meditations[i], questions[i], aves[i])
    
    texte += "\n\nChapelet Tazzz Bot – Basé sur la plasticité cérébrale et la répétition rythmée.\nCopyright Dr Tazemda"
    return texte

# ------------------ MODE PERSONNEL (mock mais solide) ------------------
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
**Notre Père** : "Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes. Je choisis ma lucidité." *(à répéter 3 vezes)*  
**Je vous salue Marie** : {mantra} *(à répéter 10 vezes)*  
**Gloire au Père** : "Je remercie Dieu et l'univers pour ses réalisations dans ma vie et cette transformation profonde." *(à répéter 3 vezes)*
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

# ------------------ ROUTES ------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    mode = data.get('mode')
    if mode == 'expertise':
        domaine = data.get('domaine')
        if not domaine:
            return jsonify({'error': 'Domaine requis'}), 400
        chapelet = generer_chapelet_expertise(domaine)
        sauvegarder_chapelet('expertise', domaine, chapelet)
        return jsonify({'chapelet': chapelet})
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
            chapelet = generer_chapelet_expertise(domaine)
            sauvegarder_chapelet('consultation_expertise', message, chapelet)
            return jsonify({'chapelet': chapelet, 'message_info': '🔍 Type détecté : EXPERTISE'})
        else:
            defauts = ["Je manque de discipline"] * 5
            chapelet = generate_mock_personnel(defauts)
            sauvegarder_chapelet('consultation_personnel', message, chapelet)
            return jsonify({'chapelet': chapelet, 'message_info': '🔍 Type détecté : PERSONNEL'})
    else:
        return jsonify({'error': 'Mode invalide'}), 400

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
