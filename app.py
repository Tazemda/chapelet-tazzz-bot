import os
import sqlite3
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

# ------------------ GÉNÉRATION EXPERTISE (7 jours – dynamique) ------------------
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

def generer_contenu_pour_domaine(domaine, jour, num_concept):
    """
    Génère un texte cohérent pour une dizaine à partir du domaine saisi.
    """
    sujet = domaine.lower().strip()
    concepts_base = [
        f"Définition et enjeux de {sujet}",
        f"Principes fondamentaux de {sujet}",
        f"Méthodologie pour {sujet}",
        f"Outils et techniques de {sujet}",
        f"Indicateurs de réussite en {sujet}"
    ]
    concept = concepts_base[num_concept % len(concepts_base)]
    
    meditation = f"Exploration détaillée de {concept}. Cela inclut les aspects clés, les bonnes pratiques et les erreurs fréquentes à éviter. Exemple concret : dans le domaine de {sujet}, il est essentiel de maîtriser les bases avant d'aborder les cas complexes."
    
    question = f"Comment appliquer correctement les règles de {concept} dans une situation réelle ? Quelles sont les trois actions prioritaires à retenir ?"
    
    ave = f"Pour bien maîtriser {sujet}, il faut comprendre que {concept} repose sur des principes solides. La répétition et la pratique permettent d'ancrer ces connaissances. Chaque professionnel doit être capable de décrire et d'utiliser ces concepts sans hésitation."

    return concept, meditation, question, ave

def generate_mock_expertise(domaine):
    jours_titres = [
        "Découverte des bases",
        "Approfondissement opérationnel",
        "Cas complexes et exceptions",
        "Contrôle qualité et indicateurs",
        "Gestion des risques et plan d'action",
        "Synthèse et liens entre concepts",
        "Auto‑évaluation et perfectionnement"
    ]
    texte_complet = f"""
--- Jour 1 – {jours_titres[0]} ---

Ce chapelet est un outil de mémorisation active par répétition rythmée, basé sur la plasticité cérébrale. Tenez un vrai chapelet dans la main.

**Point d’entrée du problème** : Comment maîtriser {domaine} avec rigueur et efficacité ?

**Règle d’or** : Une pratique quotidienne et une visualisation active.

"""
    for jour in range(1, 8):
        if jour > 1:
            texte_complet += f"\n\n--- Jour {jour} – {jours_titres[jour-1]} ---\n"
        for num_concept in range(1, 6):
            concept, meditation, question, ave = generer_contenu_pour_domaine(domaine, jour, num_concept)
            texte_complet += generer_dizaine(num_concept, concept, meditation, question, ave)
    
    texte_complet += "\n\nChapelet Tazzz Bot – Basé sur la plasticité cérébrale et la répétition rythmée.\nCopyright Dr Tazemda"
    return texte_complet

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
        chapelet = generate_mock_expertise(domaine)
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
            chapelet = generate_mock_expertise(domaine)
            sauvegarder_chapelet('consultation_expertise', message, chapelet)
            return jsonify({'chapelet': chapelet, 'message_info': '🔍 Type détecté : EXPERTISE'})
        else:
            defauts = ["Je manque de discipline"] * 5
            chapelet = generate_mock_personnel(defauts)
            sauvegarder_chapelet('consultation_personnel', message, chapelet)
            return jsonify({'chapelet': chapelet, 'message_info': '🔍 Type détecté : PERSONNEL'})
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
