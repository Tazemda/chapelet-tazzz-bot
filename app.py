# ... (début identique, jusqu'à PROMPT_JOUR)

PROMPT_JOUR = """
Tu es un expert pédagogique. Domaine: "{domaine}".

Génère le **contenu complet du Jour {jour_num}** (objectif: {titre_jour}) de manière structurée.
Commence par écrire le **titre du jour** sous la forme :
## JOUR {jour_num} – {titre court et percutant adapté au domaine, en majuscules}

Puis, génère exactement **5 DIZAINES** au format suivant (ne dépasse pas 2000 tokens au total) :

**DIZAINE 1 – Concept : [nom]**
**1) Méditation** : (paragraphe dense)
**2) Notre Père** : (question problématique)
**3) Je vous salue Marie** : (paragraphe synthétique)
**4) Gloire au Père** : "Le concept [nom] est consolidé."

(répète pour DIZAINE 2 à 5)

Soigne la qualité et l’exhaustivité. Contenu adapté au domaine.
"""

def generer_jour_expertise(domaine, jour_num):
    titres_objectifs = [
        "Découverte des bases fondamentales",
        "Approfondissement des pratiques clés",
        "Cas complexes et exceptions",
        "Contrôle qualité et indicateurs",
        "Gestion des risques et plan d'action",
        "Synthèse et liens entre concepts",
        "Auto‑évaluation et perfectionnement"
    ]
    titre_objectif = titres_objectifs[jour_num-1]
    prompt = PROMPT_JOUR.format(domaine=domaine, jour_num=jour_num, titre_jour=titre_objectif)
    try:
        raw = call_deepseek(prompt, max_tokens=1600)  # valeur ajustée
        contenu = clean_markdown(raw)
        # S'assurer que le contenu commence par un titre (## JOUR ...) et contient 5 dizaines
        if not contenu.startswith("## JOUR"):
            contenu = f"## JOUR {jour_num} – {titre_objectif.upper()}\n\n" + contenu
        return contenu
    except Exception as e:
        # fallback
        return f"""## JOUR {jour_num} – {titre_objectif.upper()}

**DIZAINE 1 – Introduction à {domaine}**
**1) Méditation** : (contenu temporaire)
**2) Notre Père** : ?
**3) Je vous salue Marie** : ...
**4) Gloire au Père** : consolidé.
(Dizaines 2 à 5 similaires – veuillez réessayer plus tard.)"""

# ... (reste du code inchangé)
