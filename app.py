def generer_personnel(defauts):
    """
    Génère un chapelet complet pour développement personnel
    selon le gabarit fourni par l'utilisateur.
    defauts : liste de 5 chaînes (les défauts à corriger)
    """
    # Construction du prompt unique pour l'API
    prompt = f"""
Tu vas générer un CHAPELET TAZ BOT – DÉVELOPPEMENT PERSONNEL (21 ou 66 jours).

Les 5 défauts à corriger sont :
1. {defauts[0]}
2. {defauts[1]}
3. {defauts[2]}
4. {defauts[3]}
5. {defauts[4]}

Tu dois produire le texte exactement selon le modèle ci-dessous. Respecte strictement la structure, les titres, les retours à la ligne. Les parties entre crochets [ ] doivent être remplacées par du contenu adapté aux défauts correspondants.

Voici le modèle à suivre :

CHAPELET TAZ BOT – 21 ou 66 JOURS 
COMMENT L’UTILISER
. Vous munir d'un chapelet que vous égrènerez pendant vos prières · Chaque jour pendant 21 ou 66 jours, de préférence la même heure : lis ce texte à voix haute ou mentalement, dans l’ordre, sans rien changer. Si vous sautez, recommencez !· Durée : environ 25 minutes.· A un moment calme.· Tu peux imprimer cette page et cocher les jours sur un calendrier.

DÉBUT (Crucifix et premiers grains)
Signe de croix : “Au nom de mon engagement, de ma lucidité et de ma persévérance.”
Crucifix (1er grain) – prière d’ouverture : “Je ne subis plus ma vie. Je deviens l’acteur de chaque heure.”
3 premiers Ave Maria (grains initiaux) :
1er Ave : “[une phrase positive qui évoque le lâcher-prise des errances passées, adaptée au premier défaut]”
2e Ave : “[une phrase positive sur la constance dans l’action, adaptée au second défaut]”
3e Ave : “[une phrase positive sur le mérite d’un travail et d’une stabilité, adaptée au troisième défaut]”
Gloire au Père (après les 3 Ave) : “Je rends grâce à la vie pour ce nouveau départ.”

---
MYSTÈRE 1 – LE LEVER ET L’ACTION MATINALE
Méditation : [une courte visualisation (3‑4 phrases) qui décrit une situation d’échec liée au premier défaut, puis la version corrigée positive avec une action concrète. Inspire-toi de l’exemple mais personnalise.] Je me vois au matin, allongé, le téléphone à la main. Je ressens la lourdeur, les heures qui glissent. Puis je me vois poser le téléphone, me lever d’un bloc, ouvrir la fenêtre. Mon corps obéit. Je choisis ce lever victorieux.
Notre Père : “Mon cerveau, par sa plasticité infinie, se réorganise chaque jour. Je deviens maître de mon attention et de mes actes. Je choisis ma lucidité.”
10 × Ave Maria (le même pour tous les mystères) : “[une phrase courte qui corrige les 5 défauts à la fois, en commençant par ‘Je me lève tôt, je range ma vie, je termine ce que je commence, je sors chaque jour, et j’attire un travail prospère.’ mais adaptée aux 5 défauts concrets]”
Gloire au Père : “Je remercie Dieu et l’univers pour ses réalisations dans ma vie et cette transformation profonde.”

---
MYSTÈRE 2 – L’ORDRE ET L’AGENDA TENU
Méditation : [visualisation adaptée au deuxième défaut. Inspire-toi de : Je revois un jour où mon désordre m’a fait rater une échéance… puis la version positive avec agenda]
Notre Père : idem
10 × Ave Maria : (identique au précédent)
Gloire au Père : idem

---
MYSTÈRE 3 – LA CONSTANCE ET LA FINITION DES PROJETS
Méditation : [adaptée au troisième défaut – projet abandonné, puis petite action quotidienne tenue]
Notre Père : idem
10 × Ave Maria : (identique)
Gloire au Père : idem

---
MYSTÈRE 4 – LA SORTIE ET LA RENCONTRE DU MONDE
Méditation : [adaptée au quatrième défaut – enfermement, scrolling, sortie et connexion avec le monde]
Notre Père : idem
10 × Ave Maria : (identique)
Gloire au Père : idem

---
MYSTÈRE 5 – LA CONFIANCE EN L’EMPLOI ET LA PROSPÉRITÉ
Méditation : [adaptée au cinquième défaut – candidatures, découragement, puis réseau, succès, salaire, famille]
Notre Père : idem
10 × Ave Maria : (identique)
Gloire au Père : idem

---
FIN DU CHAPELET (après le 5e mystère)
Salve Regina : “Ô volonté retrouvée, sois ma lumière et ma force.”
Mantra final : “Ce chapelet de 21 ou 66 jours ancre en moi la discipline joyeuse et l’action efficace.”
Signe de croix final : “Au nom de mon engagement, de ma lucidité et de ma persévérance – ainsi soit-il.”

IMPORTANT :
- Ne rajoute aucun commentaire en dehors du texte.
- Remplace TOUS les [texte] par des phrases concrètes, personnalisées, positives (sans négation).
- La phrase du Ave Maria unique doit être la même pour les 5 mystères.
- Les méditations doivent être cohérentes avec le défaut de chaque mystère.

Génère le texte complet maintenant.
"""
    try:
        raw = call_deepseek(prompt, max_tokens=3500)
        # Nettoie les éventuels caractères markdown superflus
        contenu = clean_markdown(raw)
        contenu = remove_markdown_chars(contenu)
        return contenu
    except Exception as e:
        # Fallback si l'API échoue (comme avant)
        fallback = f"CHAPELET TAZ BOT – DÉVELOPPEMENT PERSONNEL (version temporaire)\n\n"
        fallback += f"Défauts : {', '.join(defauts)}\n\n"
        fallback += "Une erreur technique est survenue. Veuillez réessayer ultérieurement.\n"
        return fallback
