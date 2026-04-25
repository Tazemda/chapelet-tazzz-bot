import os
import re
import sqlite3
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tazbot-secret-key")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# Configuration robuste
MAX_RETRIES = 3
INITIAL_MAX_TOKENS = 4000  # ≥ 3500 comme demandé
TIMEOUT = 200  # ≥ 180s comme demandé
TOKEN_INCREMENT = 500  # augmentation en cas de troncature

def call_deepseek(prompt, max_tokens=INITIAL_MAX_TOKENS, retry_count=0):
    """Appelle l'API DeepSeek avec retries et gestion de timeout robuste"""
    if not DEEPSEEK_API_KEY:
        raise Exception("Clé API manquante")
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}", 
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": max_tokens
    }
    
    last_exception = None
    
    for attempt in range(MAX_RETRIES):
        try:
            print(f"🔄 Appel API - Tentative {attempt + 1}/{MAX_RETRIES} - max_tokens={max_tokens}")
            resp = requests.post(
                DEEPSEEK_API_URL, 
                headers=headers, 
                json=payload, 
                timeout=TIMEOUT
            )
            
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                print(f"✅ Réponse reçue - Longueur: {len(content)} caractères")
                return content
            elif resp.status_code == 429:  # Rate limit
                wait_time = (attempt + 1) * 5
                print(f"⚠️ Rate limit - Attente {wait_time}s")
                time.sleep(wait_time)
                last_exception = Exception(f"Rate limit - tentative {attempt + 1}")
            else:
                raise Exception(f"API error {resp.status_code}: {resp.text[:200]}")
                
        except requests.exceptions.Timeout:
            last_exception = Exception(f"Timeout - tentative {attempt + 1}")
            if attempt < MAX_RETRIES - 1:
                print(f"⏱️ Timeout - Nouvelle tentative dans 3s")
                time.sleep(3)
        except Exception as e:
            last_exception = e
            if attempt < MAX_RETRIES - 1:
                print(f"❌ Erreur: {str(e)} - Nouvelle tentative")
                time.sleep(2)
    
    raise Exception(f"Échec après {MAX_RETRIES} tentatives: {str(last_exception)}")

def compter_dizaines(contenu):
    """Compte le nombre de DIZAINES dans le contenu"""
    # Cherche les motifs "DIZAINE X" ou "DIZAINE X –"
    pattern = r'DIZAINE\s+\d+'
    matches = re.findall(pattern, contenu, re.IGNORECASE)
    return len(matches)

def clean_markdown(text):
    """Nettoie le markdown indésirable"""
    text = re.sub(r'```[\s\S]*?```', '', text)
    return text.replace('`', '').strip()

def init_db():
    """Initialise la base de données"""
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

# ================= EXPERTISE (7 jours, titres dynamiques) =================
PROMPT_JOUR = """
Tu es un expert pédagogique spécialisé dans la création de programmes d'apprentissage 
structurés en 7 jours. Le domaine spécifique à traiter est : "{domaine}".

⚠️ CONSIGNES CRITIQUES À RESPECTER ABSOLUMENT :

1. ADAPTATION AU DOMAINE : Tout le contenu que tu génères doit être 100% spécifique au 
   domaine "{domaine}". Utilise sa terminologie exacte, ses concepts propres, ses 
   problématiques particulières. Ne te réfère à AUCUN autre domaine, même pas à titre 
   d'exemple. Le contenu doit donner l'impression d'avoir été écrit par un expert 
   de "{domaine}".

2. TITRE DU JOUR (obligatoire, exactement ce format) :
   ## **JOUR {jour_num} – [TITRE EN MAJUSCULES, ADAPTÉ AU DOMAINE]**
   
   Exemple pour le domaine "prévention des escarres" :
   ## **JOUR 1 – ÉVALUATION DES RISQUES ET ÉCHELLES DE BRADEN**

3. STRUCTURE DE CHAQUE DIZAINE (EXACTEMENT 5 DIZAINES, OBLIGATOIRE) :

   Chaque dizaine doit suivre STRICTEMENT ce format :

   **DIZAINE [numéro] – Concept : [nom du concept spécifique au domaine]**
   
   **Méditation synthèse générale (gros grain)** : [Paragraphe dense de 5-8 phrases avec définitions précises, mécanismes, données chiffrées si pertinent, et exemples concrets tirés du domaine. Doit être un contenu substantiel et informatif.]
   
   **Notre Père** (répète ceci 3 x – pas de graines) : [Une question problématique ouverte qui pousse à la réflexion approfondie sur le concept. Pas une simple définition, mais une interrogation qui stimule la pensée critique.]
   
   **Je vous salue Marie** (répète ceci 10 x – les 10 petites graines) : [Un paragraphe synthétique de 4-6 phrases, facile à mémoriser et à répéter, qui capture l'essence du concept. Utilise des formulations percutantes et des associations d'idées.]
   
   **Gloire au Père** (répète ceci 3 x) : "Le concept [nom du concept] est consolidé par [mécanisme d'ancrage spécifique]."

4. RÈGLES DE COMPLÉTUDE :
   - Tu DOIS générer les 5 DIZAINES complètes, de DIZAINE 1 à DIZAINE 5.
   - Chaque DIZAINE doit être entièrement rédigée, avec tous les sous-composants.
   - Aucune abréviation, aucun placeholder comme "[...]" ou "(à compléter)".
   - Le contenu doit être directement utilisable pour un apprentissage autonome.

5. PROGRESSION PÉDAGOGIQUE :
   Le jour {jour_num} se concentre sur l'objectif : {titre_objectif}
   Adapte le niveau de complexité et la nature des concepts à cet objectif.

Génère maintenant le contenu complet du **Jour {jour_num}** pour le domaine "{domaine}".
"""

def generer_jour_expertise(domaine, jour_num):
    """Génère le contenu d'un jour avec vérification robuste des 5 dizaines"""
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
    prompt = PROMPT_JOUR.format(
        domaine=domaine, 
        jour_num=jour_num, 
        titre_objectif=titre_objectif
    )
    
    max_tokens = INITIAL_MAX_TOKENS
    
    for attempt in range(MAX_RETRIES):
        try:
            raw = call_deepseek(prompt, max_tokens=max_tokens)
            contenu = clean_markdown(raw)
            
            # Vérifie le titre du jour
            if not re.search(r'##\s*\*\*JOUR\s+\d+', contenu, re.IGNORECASE):
                print(f"⚠️ Titre manquant - Ajout du titre")
                contenu = f"## **JOUR {jour_num} – {titre_objectif.upper()}**\n\n{contenu}"
            
            # COMPTE LES DIZAINES
            nb_dizaines = compter_dizaines(contenu)
            print(f"📊 Jour {jour_num} - {nb_dizaines} dizaines trouvées (max_tokens={max_tokens})")
            
            if nb_dizaines >= 5:
                print(f"✅ Jour {jour_num} validé avec {nb_dizaines} dizaines")
                return contenu
            else:
                print(f"⚠️ Seulement {nb_dizaines}/5 dizaines - Augmentation des tokens")
                max_tokens += TOKEN_INCREMENT
                
        except Exception as e:
            print(f"❌ Erreur tentative {attempt + 1} pour jour {jour_num}: {e}")
            if attempt == MAX_RETRIES - 1:
                return generer_fallback(domaine, jour_num, titre_objectif)
    
    # Si on arrive ici avec moins de 5 dizaines après tous les essais
    print(f"⚠️ Échec génération complète - Utilisation fallback")
    return generer_fallback(domaine, jour_num, titre_objectif)

def generer_fallback(domaine, jour_num, titre_objectif):
    """Version de secours structurée mais signalée comme temporaire"""
    return f"""## **JOUR {jour_num} – {titre_objectif.upper()}** (version de secours)

**⚠️ Contenu temporaire - Veuillez régénérer ce jour pour un contenu optimal**

**DIZAINE 1 – Concept : Introduction à {domaine}**
**Méditation synthèse générale (gros grain)** : Le domaine "{domaine}" constitue un champ de connaissances essentiel qui mérite une exploration approfondie. Ses fondements reposent sur des principes établis par la recherche et la pratique. Cette méditation vous invite à considérer l'importance de maîtriser ces concepts fondamentaux pour votre développement professionnel.
**Notre Père** (répète ceci 3 x – pas de graines) : Quelle est la question fondamentale que je dois me poser pour vraiment comprendre les enjeux de "{domaine}" ?
**Je vous salue Marie** (répète ceci 10 x – les 10 petites graines) : La maîtrise de "{domaine}" transforme ma pratique quotidienne. Chaque concept appris devient un outil puissant. La répétition consolide mes connaissances. L'expertise se construit jour après jour. Je deviens la référence dans ce domaine.
**Gloire au Père** (répète ceci 3 x) : "Le concept Introduction est consolidé par la répétition consciente."

**DIZAINE 2 – Concept : Principes fondamentaux**
**Méditation synthèse générale (gros grain)** : Les principes fondamentaux de "{domaine}" constituent la base sur laquelle tout l'édifice de connaissances se construit. Sans cette fondation solide, les apprentissages ultérieurs restent fragiles. Prenez le temps d'intégrer ces principes essentiels.
**Notre Père** (répète ceci 3 x – pas de graines) : Comment puis-je appliquer concrètement ces principes dans ma pratique de "{domaine}" ?
**Je vous salue Marie** (répète ceci 10 x – les 10 petites graines) : Les fondamentaux sont mes alliés. Je les révise avec plaisir. Chaque principe maîtrisé me renforce. La théorie éclaire ma pratique. L'apprentissage devient naturel.
**Gloire au Père** (répète ceci 3 x) : "Le concept Principes fondamentaux est consolidé par l'application pratique."

**DIZAINE 3 – Concept : Applications pratiques**
**Méditation synthèse générale (gros grain)** : La théorie prend tout son sens dans l'application concrète. "{domaine}" n'est pas un savoir abstrait mais une compétence vivante qui se déploie dans l'action quotidienne. Visualisez-vous en train d'appliquer ces connaissances avec aisance.
**Notre Père** (répète ceci 3 x – pas de graines) : Dans quelles situations réelles vais-je pouvoir mobiliser mes connaissances en "{domaine}" ?
**Je vous salue Marie** (répète ceci 10 x – les 10 petites graines) : Je pratique avec confiance. Chaque application renforce ma compétence. L'expérience transforme le savoir en expertise. Je progresse à chaque mise en pratique. Mes connaissances deviennent des réflexes.
**Gloire au Père** (répète ceci 3 x) : "Le concept Applications pratiques est consolidé par la mise en situation."

**DIZAINE 4 – Concept : Analyse critique**
**Méditation synthèse générale (gros grain)** : L'expertise véritable ne se contente pas d'appliquer, elle analyse et questionne. Dans "{domaine}", développer un regard critique permet d'éviter les erreurs et d'optimiser les résultats. Cette dizaine cultive votre discernement.
**Notre Père** (répète ceci 3 x – pas de graines) : Quelles sont les limites et les zones d'ombre dans ma compréhension actuelle de "{domaine}" ?
**Je vous salue Marie** (répète ceci 10 x – les 10 petites graines) : Je questionne avec intelligence. Mon analyse s'affine chaque jour. Le doute constructif me guide. Je repère les nuances importantes. Ma pensée devient plus précise.
**Gloire au Père** (répète ceci 3 x) : "Le concept Analyse critique est consolidé par le questionnement méthodique."

**DIZAINE 5 – Concept : Synthèse et consolidation**
**Méditation synthèse générale (gros grain)** : La synthèse des apprentissages permet de créer des liens durables entre les concepts. "{domaine}" forme maintenant un tout cohérent dans votre esprit. Cette dernière dizaine ancre définitivement les acquis de cette session.
**Notre Père** (répète ceci 3 x – pas de graines) : Quels sont les trois apprentissages les plus importants que je retiens de cette session sur "{domaine}" ?
**Je vous salue Marie** (répète ceci 10 x – les 10 petites graines) : Je consolide mes acquis avec gratitude. Les connexions se renforcent dans mon cerveau. Ma compréhension est maintenant intégrée. Je suis fier de mon parcours d'apprentissage. L'expertise devient ma seconde nature.
**Gloire au Père** (répète ceci 3 x) : "Le concept Synthèse est consolidé par l'intégration globale de {domaine}." """

# ================= DÉVELOPPEMENT PERSONNEL (simplifié) =================
def generer_personnel(defauts):
    """Génère le chapelet de développement personnel"""
    notre_pere = "Mon cerveau, par sa plasticité infinie, se réorganise chaque jour."
    resultats = []
    
    for i, d in enumerate(defauts, 1):
        prompt = f"""Mystère {i} – {d}
**Méditation synthèse générale (gros grain)** : souvenir d'un échec lié à {d} puis visualisation positive de la transformation.
**Notre Père** (répète ceci 3 x – pas de graines) : {notre_pere}
**Je vous salue Marie** (répète ceci 10 x – les 10 petites graines) : phrase courte positive corrigeant spécifiquement {d}
**Gloire au Père** (répète ceci 3 x) : Merci pour la transformation en cours."""
        
        try:
            raw = call_deepseek(prompt, max_tokens=500)
            resultats.append(clean_markdown(raw))
        except Exception as e:
            print(f"Erreur personnel mystère {i}: {e}")
            resultats.append(f"""**Mystère {i} – {d}** (version de secours)
**Méditation synthèse générale (gros grain)** : Visualisation de la transformation positive concernant {d}.
**Notre Père** (répète ceci 3 x – pas de graines) : {notre_pere}
**Je vous salue Marie** (répète ceci 10 x – les 10 petites graines) : Je transforme {d} en force positive.
**Gloire au Père** (répète ceci 3 x) : Merci pour le changement en cours.""")
    
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
    
    try:
        contenu = generer_jour_expertise(domaine, int(jour))
        return jsonify({'contenu': contenu})
    except Exception as e:
        print(f"❌ Erreur route expertise: {e}")
        return jsonify({'error': f'Erreur de génération: {str(e)}'}), 500

@app.route('/generer_personnel', methods=['POST'])
def generer_personnel_route():
    data = request.get_json()
    defauts = data.get('defauts')
    
    if not defauts or len(defauts) != 5:
        return jsonify({'error': '5 défauts requis'}), 400
    
    try:
        contenu = generer_personnel(defauts)
        return jsonify({'contenu': contenu})
    except Exception as e:
        print(f"❌ Erreur route personnel: {e}")
        return jsonify({'error': f'Erreur de génération: {str(e)}'}), 500

@app.route('/feedback', methods=['POST'])
def feedback():
    data = request.get_json()
    note = data.get('note')
    commentaire = data.get('commentaire')
    
    if note is None or commentaire is None:
        return jsonify({'error': 'Note et commentaire requis'}), 400
    
    try:
        conn = sqlite3.connect('tazbot.db')
        c = conn.cursor()
        c.execute("INSERT INTO feedback (date, note, commentaire) VALUES (?, ?, ?)",
                  (str(datetime.now()), note, commentaire))
        conn.commit()
        conn.close()
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"❌ Erreur feedback: {e}")
        return jsonify({'error': 'Erreur sauvegarde'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
