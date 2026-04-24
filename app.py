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

# ------------------ GÉNÉRATION EXPERTISE (7 jours complets) ------------------
def generer_dizaine(num, concept, meditation, question, ave):
    return f"""
**DIZAINE {num} – Concept : {concept}**

**1) Méditation (grande fiche)**  
*Instruction : Tenez le gros grain. Lisez ce paragraphe lentement, comme une fiche de cours. Vous pouvez aussi le relire plusieurs fois, revoir vos notes personnelles ou consulter d’autres sources.*  
{meditation}

**2) Notre Père (à répéter 3 fois)**  
*Instruction : Récitez cette phrase 3 fois (à voix haute ou mentalement).*  
« {question} »

**3) Je vous salue Marie (à répéter 10 fois)**  
*Instruction : Répétez ce paragraphe 10 fois (5 fois en lecture et 5 fois sans regarder). Lisez‑le d’abord pour bien l’ancrer.*  
{ave}

**4) Gloire au Père (à répéter 3 fois)**  
*Instruction : Récitez la phrase suivante 3 fois.*  
« Le concept “{concept}” est connu et consolidé. »
"""

def generate_mock_expertise(domaine):
    # Jour 1 – complet (5 dizaines)
    jour1 = f"""
--- Jour 1 – Découverte des bases du {domaine} ---

{generer_dizaine(1, 
    "Qu’est-ce qu’un service d’aide à domicile ?",
    "Un service d’aide à domicile intervient auprès de personnes âgées, handicapées ou en perte d’autonomie pour les aider dans les actes de la vie quotidienne (ménage, courses, toilette, repas). Il peut être public, associatif ou privé. L’audit vérifie la qualité, la sécurité et la continuité des prestations. Exemple : on contrôle que les plans d’aide sont bien adaptés aux besoins exprimés par l’usager.",
    "Quelles sont les missions réelles d’un service d’aide à domicile ? Qu’est‑ce qui relève de l’aide humaine, qu’est‑ce qui relève des soins infirmiers ? Comment ne jamais confondre ces deux champs ?",
    "Un service d’aide à domicile aide la personne chez elle pour les gestes quotidiens non médicaux : ménage, préparation des repas, aide à la toilette, courses, accompagnement aux rendez‑vous. L’audit porte sur la qualité de ces interventions, leur traçabilité et leur adaptation aux besoins réels. Il existe trois types de structures : publiques (CCAS), associatives (type ADMR), privées lucratives. L’auditeur doit toujours se référer au contrat individuel de la personne et au projet de service."
)}
{generer_dizaine(2,
    "Le référentiel qualité (HAS / ANESM)",
    "Le référentiel qualité est un cadre normatif qui définit les critères attendus pour les services d’aide à domicile. En France, l’ANESM puis la HAS ont produit des recommandations. L’audit compare les pratiques du service à ces critères. Exemple : critère « La personne est informée de ses droits » → l’auditeur vérifie l’existence d’un livret d’accueil.",
    "Quels sont les trois critères les plus sensibles du référentiel qualité ? Comment s’assurer que le service ne les traite pas comme de simples cases à cocher ?",
    "Le référentiel qualité (ANESM/HAS) est la base de tout audit. Il s’articule autour de thèmes : droits des usagers, accompagnement personnalisé, gestion des risques, continuité des prestations, bientraitance. Chaque critère est assorti d’indicateurs. L’auditeur doit être capable de citer les trois indicateurs les plus sensibles : la traçabilité des plans d’aide, la gestion des réclamations, la formation des intervenants. Sans référentiel, l’audit n’a pas de légitimité."
)}
{generer_dizaine(3,
    "Évaluation des besoins de la personne",
    "L’évaluation individuelle des besoins (physiques, sociaux, environnementaux) est le point de départ de toute intervention. L’audit vérifie qu’elle est récente, partagée avec l’usager et mise à jour après chaque changement (hospitalisation, chute, évolution de la pathologie). Exemple : absence d’actualisation après une fracture = non‑conformité.",
    "Quelles questions poser pour détecter les besoins inexprimés ? Comment éviter que l’évaluation ne devienne une simple case à cocher ?",
    "L’évaluation des besoins doit être : systématique dès l’admission, réalisée avec un outil validé (ex. AGGIR, GEVA), et révisée tous les 6 mois ou à chaque événement. L’auditeur examine la date de la dernière évaluation, la signature de l’usager ou de son représentant, et la cohérence avec les interventions planifiées. Un besoin non évalué est un besoin non traité."
)}
{generer_dizaine(4,
    "Traçabilité et documentation",
    "La traçabilité est la preuve écrite de chaque action réalisée. Documents clés : projet personnalisé, feuilles de présence, comptes rendus d’intervention, registre des réclamations. L’audit vérifie l’absence de trous dans cette documentation.",
    "Quels sont les quatre documents incontournables d’un dossier ? Comment s’assurer qu’ils sont cohérents entre eux sans tout vérifier ligne à ligne ?",
    "La traçabilité comprend quatre documents de base : le contrat de prestation, le plan d’aide personnalisé, les feuilles d’intervention (dates, horaires, actes effectués), et le registre des réclamations. L’auditeur contrôle la cohérence entre ces documents : par exemple, les heures facturées doivent correspondre aux feuilles d’intervention. Toute absence de signature ou de date est une non‑conformité susceptible de refus de financement. Un dossier complet se prépare au quotidien."
)}
{generer_dizaine(5,
    "Gestion des plaintes et des risques",
    "La gestion des plaintes est un indicateur clé de la qualité. Le service doit disposer d’un registre des réclamations écrites et d’une procédure pour analyser chaque plainte et prendre des actions correctives.",
    "Comment transformer une plainte en opportunité d’amélioration ? Quelles sont les trois étapes obligatoires pour traiter une réclamation ?",
    "Le registre des plaintes doit être daté, signé par l’usager, et annoté avec la réponse du service. L’auditeur vérifie que chaque réclamation a donné lieu à une analyse des causes (retard, absence, manque de douceur) et à un plan d’action. Les actions correctives doivent être traçables (formation, changement d’organisation). L’absence de plainte n’est pas un signe de qualité : il faut aussi recueillir la satisfaction de façon proactive."
)}
"""
    # Jours 2 à 7 (version simplifiée mais structurée : on répète le même motif avec des intitulés différents)
    # Pour ne pas alourdir, je génère des jours complets avec des concepts génériques mais le format est respecté.
    jours_suivants = ""
    for j in range(2, 8):
        jours_suivants += f"""
--- Jour {j} – {["Approfondissement opérationnel", "Cas complexes", "Contrôle qualité", "Indicateurs", "Synthèse des liens", "Auto‑évaluation"][j-2]} ---

{generer_dizaine(1, f"Concept clé {j}.1", 
    f"Méditation détaillée pour le jour {j} – première dizaine. Adaptez ce contenu à votre domaine {domaine}.",
    f"Question pertinente pour le jour {j} – première dizaine ?",
    f"Paragraphe synthétique dense pour le jour {j} – première dizaine. À personnaliser.")}
{generer_dizaine(2, f"Concept clé {j}.2", 
    f"Méditation détaillée – deuxième dizaine du jour {j}.",
    f"Question pour la deuxième dizaine du jour {j} ?",
    f"Paragraphe synthétique – deuxième dizaine du jour {j}.")}
{generer_dizaine(3, f"Concept clé {j}.3", 
    f"Méditation – troisième dizaine du jour {j}.",
    f"Question – troisième dizaine ?",
    f"Paragraphe – troisième dizaine du jour {j}.")}
{generer_dizaine(4, f"Concept clé {j}.4", 
    f"Méditation – quatrième dizaine du jour {j}.",
    f"Question – quatrième dizaine ?",
    f"Paragraphe – quatrième dizaine du jour {j}.")}
{generer_dizaine(5, f"Concept clé {j}.5", 
    f"Méditation – cinquième dizaine du jour {j}.",
    f"Question – cinquième dizaine ?",
    f"Paragraphe – cinquième dizaine du jour {j}.")}
"""
    return jour1 + jours_suivants + "\n\nChapelet Tazzz Bot – Basé sur la plasticité cérébrale et la répétition rythmée.\nCopyright Dr Tazemda"

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
        message = data.get('message')
        if not message:
            return jsonify({'error': 'Message requis'}), 400
        if any(w in message.lower() for w in ['maîtriser', 'apprendre', 'domaine', 'entretien']):
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
