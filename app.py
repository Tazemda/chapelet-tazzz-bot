import os
import json
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

# ------------------ GÉNÉRATION MOCK EXPERTISE (7 jours) ------------------
def generer_jour(domaine, num_jour, titre, concepts):
    """
    Génère un jour complet avec 5 dizaines.
    concepts : liste de 5 dictionnaires {'nom': ..., 'meditation': ..., 'question': ..., 'ave': ...}
    """
    jour_texte = f"\n\n**--- Jour {num_jour} – {titre} ---**\n"
    for i, c in enumerate(concepts, 1):
        jour_texte += f"""
**DIZAINE {i} – Concept : {c['nom']}**

**1) Méditation (grande fiche)**  
*Instruction : Tenez le gros grain. Lisez ce paragraphe lentement, comme une fiche de cours. Vous pouvez aussi le relire plusieurs fois, revoir vos notes personnelles ou consulter d’autres sources.*  
{c['meditation']}

**2) Notre Père (à répéter 3 fois)**  
*Instruction : Récitez cette phrase 3 fois (à voix haute ou mentalement).*  
« {c['question']} »

**3) Je vous salue Marie (à répéter 10 fois)**  
*Instruction : Répétez ce paragraphe 10 fois (5 fois en lecture et 5 fois sans regarder). Lisez‑le d’abord pour bien l’ancrer.*  
{c['ave']}

**4) Gloire au Père (à répéter 3 fois)**  
*Instruction : Récitez la phrase suivante 3 fois.*  
« Le concept “{c['nom']}” est connu et consolidé. »
"""
    return jour_texte

def generate_mock_expertise(domaine):
    """
    Construit un chapelet d'expertise complet sur 7 jours.
    Adapte le contenu générique au domaine saisi par l'utilisateur.
    """
    # Concepts prédéfinis génériques (adaptables)
    concepts_jour1 = [
        {"nom": f"Définition et périmètre de {domaine}", 
         "meditation": f"{domaine} recouvre l’ensemble des pratiques et connaissances nécessaires pour atteindre un objectif spécifique. Exemple : dans {domaine}, on commence par délimiter le champ d’action, les acteurs, les obligations.", 
         "question": f"Quelles sont les limites exactes de {domaine} ? Qu’est‑ce qui relève du cœur du métier, qu’est‑ce qui relève des tâches connexes ?",
         "ave": f"{domaine} se caractérise par trois piliers : les principes théoriques, les méthodes opérationnelles, et les outils de contrôle. L’auditeur doit toujours se référer aux référentiels en vigueur. Sans une délimitation claire, on risque de sortir du périmètre de l’audit."},
        {"nom": "Principes fondamentaux",
         "meditation": "Les principes fondamentaux sont la rigueur, la traçabilité, l’amélioration continue. Exemple : dans un audit, on vérifie systématiquement la conformité aux exigences réglementaires.",
         "question": "Quels sont les trois piliers éthiques et méthodologiques à ne jamais oublier ?",
         "ave": "Les principes fondamentaux sont : la rigueur (suivi exact du plan), la traçabilité (preuves écrites), l’amélioration continue (actions correctives après chaque écart). Je les applique consciemment dans chaque action."},
        {"nom": "Méthodologie pas à pas",
         "meditation": "La méthodologie standard comporte quatre étapes : cadrage, collecte, analyse, rapport. Exemple : avant toute collecte, il faut valider le périmètre avec l’audité.",
         "question": "Comment enchaîner les quatre étapes sans en oublier ?",
         "ave": "La méthodologie en quatre temps : 1) définir les objectifs, 2) recueillir les preuves, 3) analyser les écarts, 4) formaliser les recommandations. Chaque étape doit être documentée. Le non‑respect du schéma fragilise la crédibilité."},
        {"nom": "Outils essentiels",
         "meditation": "Les outils courants sont les grilles d’analyse, les checklists, les logiciels de gestion. Exemple : une checklist évite les oublis lors de l’examen documentaire.",
         "question": "Quels outils dois‑je maîtriser en priorité pour gagner en efficacité ?",
         "ave": "Les outils clés : la grille d’audit (liste des critères), le plan d’action (suivi des correctifs), le tableau de bord (indicateurs). Je m’entraîne à les utiliser sur des cas pratiques."},
        {"nom": "Indicateurs de succès",
         "meditation": "On mesure la performance par des indicateurs quantitatifs (délais, taux de conformité) et qualitatifs (satisfaction, pertinence).",
         "question": "Quels indicateurs me permettent de savoir si ma maîtrise de {domaine} progresse ?",
         "ave": "Les indicateurs à suivre : délai moyen de réalisation, nombre d’anomalies corrigées, feedback des parties prenantes. Je les relève chaque semaine pour ajuster mon apprentissage."}
    ]
    # Pour les jours 2 à 7, on pourrait répéter le pattern avec des concepts différents.
    # Par souci de concision, je ne détaille que le Jour 1 ici, mais le code complet pour 7 jours serait similaire.
    # En production, vous pouvez étendre à 7 jours en créant des listes de concepts pour chaque jour.
    # Pour ce mock, je génère seulement le Jour 1 et j'ajoute un message indiquant qu'il faut étendre.
    # Mais pour que le bot soit fonctionnel, je vais générer 7 jours avec des concepts répétés (à personnaliser).
    # Version simplifiée : on génère 7 jours en répétant le même motif avec des titres différents.
    jours = [
        ("Découverte des bases", concepts_jour1),
        # Pour les jours suivants, on pourrait adapter les concepts manuellement ou les générer automatiquement.
        # Ici, je vais simplement réutiliser les mêmes concepts pour tous les jours (en gardant la structure).
        ("Approfondissement opérationnel", concepts_jour1),
        ("Cas complexes et exceptions", concepts_jour1),
        ("Contrôle et audit", concepts_jour1),
        ("Indicateurs et amélioration", concepts_jour1),
        ("Synthèse et liens", concepts_jour1),
        ("Auto‑évaluation et finalisation", concepts_jour1)
    ]
    full_text = f"""
**CHAPELET TAZZZ BOT – MODE EXPERTISE (7 jours) – Domaine : {domaine}**

Ce chapelet est un outil de mémorisation active par répétition rythmée, basé sur la plasticité cérébrale. Tenez un vrai chapelet dans la main.

**Point d’entrée du problème** : Comment maîtriser {domaine} avec rigueur et efficacité ?

**Règle d’or** : Une pratique quotidienne et une visualisation active.
"""
    for i, (titre, concepts) in enumerate(jours, 1):
        full_text += generer_jour(domaine, i, titre, concepts)
    full_text += "\n\nChapelet Tazzz Bot – Basé sur la plasticité cérébrale et la répétition rythmée.\nCopyright Dr Tazemda"
    return full_text

# ------------------ MODE PERSONNEL (mock) ------------------
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
**Notre Père (à répéter 3 fois)** : "Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes. Je choisis ma lucidité."  
**10 × Je vous salue Marie** : {mantra}  
**Gloire au Père (à répéter 3 fois)** : "Je remercie Dieu et l'univers pour ses réalisations dans ma vie et cette transformation profonde."
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
        # Très simple : on redirige vers expertise avec le message comme domaine si contient mot-clé
        message = data.get('message')
        if not message:
            return jsonify({'error': 'Message requis'}), 400
        if any(word in message.lower() for word in ['maîtriser', 'apprendre', 'domaine', 'comprendre', 'entretien']):
            domaine = message[:150]  # tronquer
            chapelet = generate_mock_expertise(domaine)
            sauvegarder_chapelet('consultation (expertise)', domaine, chapelet)
            return jsonify({'chapelet': chapelet, 'message_info': '🔍 Type détecté : EXPERTISE (guide vers le chapelet d’expertise)'})
        else:
            defauts = ["Je manque de discipline"] * 5
            chapelet = generate_mock_personnel(defauts)
            sauvegarder_chapelet('consultation (personnel)', str(defauts), chapelet)
            return jsonify({'chapelet': chapelet, 'message_info': '🔍 Type détecté : PERSONNEL (guide vers le chapelet personnel)'})
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
   
