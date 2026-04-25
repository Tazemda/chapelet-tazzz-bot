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

def call_deepseek(prompt, max_tokens=4000, temperature=0.7):
    """
    Appel API DeepSeek optimisé avec gestion d'erreur améliorée
    """
    if not DEEPSEEK_API_KEY:
        raise Exception("Clé API manquante")
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}", 
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system", 
                "content": "Tu es un expert pédagogique qui fournit des réponses COMPLÈTES et DÉTAILLÉES sans jamais tronquer le contenu."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": 0.9,
        "frequency_penalty": 0.1,
        "presence_penalty": 0.1
    }
    
    try:
        resp = requests.post(
            DEEPSEEK_API_URL, 
            headers=headers, 
            json=payload, 
            timeout=180  # Timeout augmenté
        )
        
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            finish_reason = resp.json()["choices"][0].get("finish_reason", "")
            
            # Log pour debug
            print(f"Tokens utilisés: {resp.json().get('usage', {}).get('total_tokens', 'N/A')}")
            print(f"Raison de fin: {finish_reason}")
            
            # Si tronqué, relancer avec plus de tokens
            if finish_reason == "length":
                print("⚠️ Réponse tronquée, relance avec plus de tokens...")
                return call_deepseek(prompt, max_tokens=min(max_tokens * 2, 8000), temperature=temperature)
            
            return content
        else:
            raise Exception(f"API error {resp.status_code}: {resp.text[:200]}")
            
    except requests.exceptions.Timeout:
        raise Exception("Timeout API - Réessayez")
    except Exception as e:
        raise Exception(f"Erreur API: {str(e)}")

def clean_markdown(text):
    """Nettoie le markdown tout en préservant le contenu"""
    # Supprime les blocs de code
    text = re.sub(r'```[\s\S]*?```', lambda m: m.group().replace('`', ''), text)
    # Supprime les backticks isolés
    text = re.sub(r'(?<!`)`(?!`)', '', text)
    return text.strip()

def init_db():
    """Initialise la base de données"""
    conn = sqlite3.connect('tazbot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS feedback
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT,
                  note INTEGER,
                  commentaire TEXT,
                  domaine TEXT,
                  jour INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# ================= EXPERTISE (7 jours, titres dynamiques) =================
PROMPT_JOUR = """Tu es un expert pédagogique de haut niveau. Domaine : "{domaine}".

**IMPORTANT**: Génère le contenu COMPLET du Jour {jour_num} sur 7 jours, SANS JAMAIS TRONQUER.
L'objectif général du jour {jour_num} est : {titre_objectif}.

Structure OBLIGATOIRE à respecter INTÉGRALEMENT :

## **JOUR {jour_num} – [TITRE PERTINENT EN MAJUSCULES ADAPTÉ AU DOMAINE]**

### **DIZAINE 1 – Concept : [Nom du concept clé]**
**1) Méditation** : Rédige un paragraphe DENSE et COMPLET (15-20 lignes) avec :
- Définition précise du concept
- 3 exemples concrets et détaillés
- Applications pratiques
- Points clés à retenir

**2) Notre Père** : Pose UNE question problématique profonde qui force la réflexion critique sur le concept.

**3) Je vous salue Marie** : Rédige un paragraphe synthétique de synthèse (10-15 lignes) à mémoriser, couvrant l'essentiel du concept.

**4) Gloire au Père** : "Le concept "[nom]" est consolidé par la répétition et la pratique."

### **DIZAINE 2 – Concept : [Nom du concept complémentaire]**
[Structure identique avec contenu COMPLET]

### **DIZAINE 3 – Concept : [Nom du concept avancé]**
[Structure identique avec contenu COMPLET]

### **DIZAINE 4 – Concept : [Nom du concept critique]**
[Structure identique avec contenu COMPLET]

### **DIZAINE 5 – Concept : [Nom du concept intégrateur]**
[Structure identique avec contenu COMPLET]

**CONCLUSION DU JOUR {jour_num}** : Rédige un paragraphe récapitulatif (8-12 lignes) synthétisant TOUS les concepts vus aujourd'hui.

ASSURE-TOI QUE LE CONTENU EST COMPLET, DÉTAILLÉ ET DIRECTEMENT UTILISABLE."""

def generer_jour_expertise(domaine, jour_num, max_retries=3):
    """
    Génère le contenu d'un jour avec mécanisme de retry anti-troncature
    """
    objectifs = [
        "Découverte des bases fondamentales et concepts clés",
        "Approfondissement des pratiques essentielles et méthodologies",
        "Analyse des cas complexes et gestion des exceptions",
        "Contrôle qualité, indicateurs de performance et monitoring",
        "Gestion des risques, anticipation et plans d'action",
        "Synthèse intégrative et liens entre tous les concepts",
        "Auto‑évaluation, perfectionnement et plan de progression"
    ]
    
    titre_objectif = objectifs[jour_num-1]
    prompt = PROMPT_JOUR.format(
        domaine=domaine, 
        jour_num=jour_num, 
        titre_objectif=titre_objectif
    )
    
    for attempt in range(max_retries):
        try:
            # Augmentation progressive des tokens si nécessaire
            max_tokens = 4000 + (attempt * 2000)
            raw = call_deepseek(prompt, max_tokens=max_tokens)
            contenu = clean_markdown(raw)
            
            # Vérifications de complétude
            if not re.search(r'##\s*\*\*JOUR\s+\d+', contenu, re.IGNORECASE):
                contenu = f"## **JOUR {jour_num} – {titre_objectif.upper()}**\n\n{contenu}"
            
            # Vérifie que les 5 dizaines sont présentes
            dizaines_count = len(re.findall(r'DIZAINE\s+\d', contenu))
            if dizaines_count >= 5:
                print(f"✅ Jour {jour_num} complet avec {dizaines_count} dizaines")
                return contenu
            else:
                print(f"⚠️ Jour {jour_num} incomplet ({dizaines_count}/5 dizaines) - Tentative {attempt + 1}")
                
        except Exception as e:
            print(f"❌ Erreur jour {jour_num} (tentative {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                return generer_contenu_secours(domaine, jour_num, titre_objectif)
    
    return generer_contenu_secours(domaine, jour_num, titre_objectif)

def generer_contenu_secours(domaine, jour_num, titre_objectif):
    """Génère un contenu de secours minimal mais structuré"""
    contenu = f"""## **JOUR {jour_num} – {titre_objectif.upper()}** (Version de secours)

⚠️ *Le contenu complet n'a pas pu être généré. Veuillez rafraîchir la page ou contacter le support.*

### **DIZAINE 1 – Fondamentaux de {domaine}**
**1) Méditation** : Prenez le temps de vous concentrer sur les bases essentielles de {domaine}. Visualisez les concepts clés et leur application concrète dans votre pratique quotidienne.
**2) Notre Père** : Quels sont les principes fondamentaux qui sous-tendent {domaine} ?
**3) Je vous salue Marie** : La maîtrise de {domaine} passe par une compréhension approfondie de ses fondements.
**4) Gloire au Père** : Le concept fondamental est consolidé.

### **DIZAINE 2 à 5 – Structure similaire**
*Contenu à régénérer - Rafraîchissez la page*

**CONCLUSION** : La progression pédagogique continue. Chaque jour apporte son lot d'apprentissages essentiels."""
    return contenu

# ================= DÉVELOPPEMENT PERSONNEL (optimisé) =================
PROMPT_PERSONNEL = """Tu es un coach en développement personnel. Génère un chapelet de transformation pour corriger ces 5 défauts.

Pour chaque défaut, suis STRICTEMENT cette structure (contenu COMPLET, jamais tronqué) :

**Mystère {numero} – {defaut}**

**Méditation** : (8-12 lignes)
- Souvenir précis d'un échec lié à ce défaut
- Visualisation détaillée d'un succès futur
- Impact transformateur

**Notre Père** : "Mon cerveau, par sa plasticité infinie, se réorganise chaque jour pour dépasser {defaut}." (Répéter 3 fois mentalement)

**Je vous salue Marie** : (Phrase positive puissante, 5-8 lignes)
- Formulation au présent
- Affirmation de la transformation
- Ancrage émotionnel positif

**Gloire au Père** : "Merci pour cette transformation en cours." (Répéter 3 fois avec gratitude)

Défauts à traiter :
{defauts}"""

def generer_personnel(defauts):
    """Génère le chapelet personnel optimisé"""
    prompt = PROMPT_PERSONNEL.format(
        defauts="\n".join([f"{i+1}. {d}" for i, d in enumerate(defauts)])
    )
    
    try:
        raw = call_deepseek(prompt, max_tokens=3000)
        contenu = clean_markdown(raw)
        
        # Vérification des 5 mystères
        mysteres_count = len(re.findall(r'Mystère\s+\d', contenu))
        if mysteres_count >= 5:
            return contenu
        else:
            # Fallback simple
            return generer_personnel_secours(defauts)
            
    except Exception as e:
        print(f"Erreur personnel: {e}")
        return generer_personnel_secours(defauts)

def generer_personnel_secours(defauts):
    """Version de secours pour le développement personnel"""
    notre_pere = "Mon cerveau, par sa plasticité infinie, se réorganise chaque jour."
    contenu = ""
    for i, defaut in enumerate(defauts, 1):
        contenu += f"""
**Mystère {i} – {defaut}**

**Méditation** : Visualisez-vous dépassant {defaut}. Ressentez la fierté et la liberté que cela procure.

**Notre Père** : "{notre_pere}" (×3)

**Je vous salue Marie** : "Je transcende {defaut} avec confiance et détermination. Chaque jour, je progresse vers ma meilleure version."

**Gloire au Père** : Merci (×3)

"""
    return contenu.strip()

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
        return jsonify({
            'contenu': contenu,
            'jour': int(jour),
            'domaine': domaine,
            'status': 'success'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generer_personnel', methods=['POST'])
def generer_personnel_route():
    data = request.get_json()
    defauts = data.get('defauts')
    
    if not defauts or len(defauts) != 5:
        return jsonify({'error': '5 défauts requis'}), 400
    
    try:
        contenu = generer_personnel(defauts)
        return jsonify({'contenu': contenu, 'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/feedback', methods=['POST'])
def feedback():
    data = request.get_json()
    note = data.get('note')
    commentaire = data.get('commentaire')
    domaine = data.get('domaine', '')
    jour = data.get('jour', 0)
    
    if note is None:
        return jsonify({'error': 'Note requise'}), 400
    
    try:
        conn = sqlite3.connect('tazbot.db')
        c = conn.cursor()
        c.execute(
            "INSERT INTO feedback (date, note, commentaire, domaine, jour) VALUES (?, ?, ?, ?, ?)",
            (str(datetime.now()), note, commentaire or '', domaine, jour)
        )
        conn.commit()
        conn.close()
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Endpoint de santé pour monitoring"""
    return jsonify({
        'status': 'healthy',
        'api_key': bool(DEEPSEEK_API_KEY),
        'timestamp': str(datetime.now())
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
