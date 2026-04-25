import os
import re
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tazbot-secret-key")

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

# ================= GÉNÉRATION LOCALE (sans API) =================
def generer_contenu_jour(domaine, jour_num):
    """Génère un contenu pédagogique complet de 5 dizaines sans appel externe."""
    titres_jours = [
        "Découverte des bases fondamentales",
        "Approfondissement des pratiques clés",
        "Cas complexes et exceptions",
        "Contrôle qualité et indicateurs",
        "Gestion des risques et plan d'action",
        "Synthese et liens entre concepts",
        "Auto‑évaluation et perfectionnement"
    ]
    titre_jour = titres_jours[jour_num-1]
    
    # Concepts génériques adaptables
    concepts = [
        f"Introduction à {domaine}",
        f"Principes clés de {domaine}",
        f"Méthodologie pour {domaine}",
        f"Outils essentiels en {domaine}",
        f"Indicateurs de succès pour {domaine}"
    ]
    
    contenu = f"## **JOUR {jour_num} – {titre_jour.upper()}**\n\n"
    for i, concept in enumerate(concepts, 1):
        contenu += f"""
**DIZAINE {i} – Concept : {concept}**

**1) Méditation (gros grain)**  
{domaine} est un domaine vaste. Par exemple, dans la pratique quotidienne, on rencontre des situations où {concept.lower()} est déterminant.  
Pour illustrer : un professionnel doit maîtriser les règles de base, éviter les erreurs fréquentes, et appliquer des solutions éprouvées.  
La connaissance de {concept.lower()} permet d’améliorer la qualité et la sécurité.

**2) Notre Père**  
« Quelle est la première action à mener pour bien appliquer {concept.lower()} dans une situation réelle ? »

**3) Je vous salue Marie** (à répéter 10 fois)  
Je retiens que {concept.lower()} repose sur trois piliers : la prévention, la réactivité et l’amélioration continue.  
En cas de doute, je me réfère aux recommandations officielles.  
La répétition régulière rend ces gestes automatiques.  
Je pratique chaque jour pour ancrer ces connaissances.  
Ainsi, je deviens compétent et fiable dans {domaine}.

**4) Gloire au Père** (à répéter 3 fois)  
« Le concept "{concept}" est consolidé. »

"""
    return contenu

# ================= MODE PERSONNEL (local) =================
def generer_personnel(defauts):
    notre_pere = "Mon cerveau, par sa plasticité infinie, se réorganise chaque jour."
    resultats = []
    for i, d in enumerate(defauts, 1):
        resultats.append(f"""
**Mystère {i} – {d}**  
**Méditation** : Je me souviens d’un moment où ce défaut m’a nui. Aujourd’hui, je visualise le comportement opposé : je me lève tôt, je range, je termine mes projets, je sors et je mène une action concrète chaque jour.  
**Notre Père** : {notre_pere} *(à répéter 3 fois)*  
**Je vous salue Marie** : Je transforme {d} en force par la répétition positive. *(10 fois)*  
**Gloire au Père** : Je remercie Dieu et l’univers pour cette transformation. *(3 fois)*
""")
    return "\n\n".join(resultats)

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
    contenu = generer_contenu_jour(domaine, int(jour))
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
