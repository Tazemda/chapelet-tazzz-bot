def generer_personnel(defauts):
    """
    Génère un chapelet avec 5 mystères, chacun explicitement lié à un défaut.
    """
    # Construction du prompt avec les défauts indexés
    prompt = f"""
Tu vas générer un CHAPELET TAZ BOT – DÉVELOPPEMENT PERSONNEL (21 ou 66 jours) en suivant EXACTEMENT la structure ci-dessous.

Les 5 défauts à corriger sont :
Mystère 1 – Défaut : {defauts[0]}
Mystère 2 – Défaut : {defauts[1]}
Mystère 3 – Défaut : {defauts[2]}
Mystère 4 – Défaut : {defauts[3]}
Mystère 5 – Défaut : {defauts[4]}

Tu DOIS utiliser le libellé du défaut (tel qu’il est écrit) dans le titre du mystère et dans la méditation.  
Exemple : si le défaut 1 est « je me lève tard », le titre du mystère 1 sera « Mystère 1 – je me lève tard ».  
La méditation décrira une situation où ce défaut a causé un problème, puis une visualisation positive de l’action opposée.

Voici le modèle à suivre (remplace [Défaut X] par le texte exact du défaut, et [Méditation X] par une visualisation adaptée) :

CHAPELET TAZ BOT – 21 ou 66 JOURS 
COMMENT L’UTILISER
... (texte identique à ton prototype)

DÉBUT (Crucifix et premiers grains)
Signe de croix : “Au nom de mon engagement, de ma lucidité et de ma persévérance.”
Crucifix : “Je ne subis plus ma vie. Je deviens l’acteur de chaque heure.”
3 premiers Ave Maria :
1er Ave : “Je laisse derrière moi le poids des errances passées, en particulier quand [premier défaut] me freinait.”
2e Ave : “Je choisis la constance dans l’action, même face à [deuxième défaut].”
3e Ave : “Je mérite un travail stable et une fierté retrouvée, malgré [troisième défaut].”
Gloire : “Je rends grâce à la vie pour ce nouveau départ.”

---
MYSTÈRE 1 – {defauts[0]}
Méditation : [Raconte un souvenir précis où ce défaut a causé un échec ou une frustration. Puis décris la nouvelle action positive qui le corrige, en utilisant le “je” présent et sans négation. Exemple : “Je me vois au matin, allongé... puis je me lève d’un bloc.”]
Notre Père : “Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes. Je choisis ma lucidité.”
10 × Ave Maria (le même pour tous les mystères) : “[Phrase unique qui corrige les 5 défauts, en commençant par ‘Je me lève tôt, je range ma vie, je termine ce que je commence, je sors chaque jour, et j’attire un travail prospère.’ mais personnalisée avec les mots des 5 défauts]”
Gloire au Père : “Je remercie Dieu et l’univers pour ses réalisations dans ma vie et cette transformation profonde.”

---
MYSTÈRE 2 – {defauts[1]}
Méditation : [adaptée au deuxième défaut – même structure]
Notre Père : (identique)
10 × Ave Maria : (identique)
Gloire : (identique)

---
MYSTÈRE 3 – {defauts[2]}
Méditation : [adaptée au troisième défaut]
Notre Père : idem
10 × Ave Maria : idem
Gloire : idem

---
MYSTÈRE 4 – {defauts[3]}
Méditation : [adaptée au quatrième défaut]
Notre Père : idem
10 × Ave Maria : idem
Gloire : idem

---
MYSTÈRE 5 – {defauts[4]}
Méditation : [adaptée au cinquième défaut]
Notre Père : idem
10 × Ave Maria : idem
Gloire : idem

---
FIN DU CHAPELET
Salve Regina : “Ô volonté retrouvée, sois ma lumière et ma force.”
Mantra final : “Ce chapelet de 21 ou 66 jours ancre en moi la discipline joyeuse et l’action efficace.”
Signe de croix final : “Au nom de mon engagement, de ma lucidité et de ma persévérance – ainsi soit-il.”

IMPORTANT : 
- N’ajoute aucun commentaire.
- Respecte exactement la structure (titres, retours à la ligne, mots exacts du début et de la fin).
- Les méditations doivent être personnalisées en fonction du défaut mentionné dans le titre.
- La phrase du Ave Maria unique doit être la même pour les 5 mystères.
Génère le texte complet maintenant.
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
