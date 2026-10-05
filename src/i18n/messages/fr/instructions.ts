/** Guide de l’utilisateur. Une page avec des ancres, à lire avant le premier envoi. */
export const instructions = {
  stage: 'Guide',
  title: 'Guide de l’utilisateur',
  lead: 'À lire une fois avant votre premier envoi. Vous saurez ce qu’il faut, ce qui arrive à votre fichier et à quoi vous attendre.',
  tocTitle: 'Sur cette page',
  sections: {
    need: 'Ce qu’il vous faut',
    upload: 'Comment envoyer',
    file: 'Ce qui arrive au fichier',
    check: 'Vérifier les valeurs',
    get: 'Ce que vous obtenez',
    share: 'Partager vos données',
    faq: 'Questions fréquentes',
  },
  need: {
    lead: 'Une analyse de sang avec neuf marqueurs, et votre âge.',
    markersTitle: 'Les neuf marqueurs',
    hsCrpNote:
      'Une numération formule sanguine et un bilan biochimique courants ne comprennent pas toujours la CRP ultrasensible. Il faut parfois la demander à part.',
    missingNote:
      'S’il manque un marqueur, la plateforme enregistre les autres valeurs mais ne calcule pas l’indice, et indique ce qui manque.',
    reportLook:
      'Un compte rendu convient s’il présente un tableau : nom du marqueur, valeur, unité et, en général, intervalle de référence.',
    oneFileNote:
      'Pour l’instant, l’indice est calculé à partir d’un seul compte rendu envoyé. Si la numération et la biochimie sont arrivées dans des fichiers séparés, chacun est enregistré, mais l’indice n’est pas calculé à partir d’eux.',
  },
  upload: {
    items: [
      'Vous pouvez envoyer un PDF, un scan ou une photo du compte rendu.',
      'Pour une photo, encadrez dans le navigateur uniquement le tableau des résultats. Laissez l’en-tête avec votre nom hors du cadre.',
      'Le serveur masque en plus les lignes personnelles avant la lecture. S’il a un doute, vous voyez l’extrait masqué et décidez de l’envoyer ou non.',
    ],
  },
  file: {
    items: [
      'Le fichier original est lu dans la mémoire du serveur et n’est pas écrit sur disque.',
      'Dans un PDF texte, un programme du serveur extrait le texte et retire les lignes personnelles. Sur un scan ou une photo, le serveur masque d’abord ces lignes.',
      'Le texte ou l’image nettoyés sont ensuite envoyés au service de reconnaissance externe Google Gemini, qui trouve les marqueurs et leurs valeurs.',
      'Seuls l’empreinte du fichier (SHA-256, qui ne permet pas de reconstituer le fichier) et les valeurs que vous confirmez sont conservés.',
    ],
  },
  check: {
    items: [
      'Vous voyez les valeurs et les unités lues à côté de chaque marqueur.',
      'Comparez-les avec votre compte rendu, corrigez les erreurs et confirmez.',
      'Tant que vous n’avez pas confirmé, rien n’est enregistré.',
    ],
  },
  get: {
    items: [
      'L’indice de recherche et sa comparaison avec votre âge civil.',
      'L’historique de vos envois et l’évolution de chaque marqueur.',
    ],
    notTitle: 'Ce que vous n’aurez pas',
    notItems: [
      'De diagnostics.',
      'De conseils de traitement.',
      'De conseils sur les compléments ou l’alimentation.',
    ],
  },
  share: {
    lead: 'La publication est désactivée par défaut. Vous pouvez l’activer ou la désactiver à tout moment dans « Mon espace → Données et consentements ».',
    shownTitle: 'Si vous l’activez, nous publions',
    shown: [
      'un ID pseudonyme, sans lien avec votre nom ;',
      'la date du prélèvement ;',
      'votre âge au prélèvement ;',
      'les codes et valeurs des marqueurs.',
    ],
    hiddenTitle: 'Nous ne publions jamais',
    hidden: ['votre nom ;', 'votre e-mail ;', 'votre date de naissance ;', 'l’ID interne du compte ;', 'les notes de votre journal.'],
    warningTitle: 'Important avant d’activer',
    warning:
      'Les lignes publiées le sont sous licence CC0. Les copies déjà téléchargées par d’autres personnes ne peuvent pas être retirées, même si vous supprimez votre compte.',
  },
  faq: [
    {
      q: 'Est-ce un diagnostic ?',
      a: 'Non. C’est un indice de recherche. Il ne nomme ni n’exclut aucune maladie.',
    },
    {
      q: 'Mon indice est supérieur à mon âge civil. Que faire ?',
      a: 'Parlez des valeurs avec un médecin. La plateforme ne donne aucun conseil sur la conduite à tenir.',
    },
    {
      q: 'À quelle fréquence faire une analyse ?',
      a: 'La plateforme ne fixe pas de calendrier. Pour comparer deux analyses honnêtement, faites-les dans les mêmes conditions : à jeun, sans maladie, sans gros effort la veille, de préférence dans le même laboratoire.',
    },
    {
      q: 'Pourquoi ma photo n’a-t-elle pas été reconnue ?',
      a: 'En général, la photo est floue, prise de biais ou le tableau est coupé. Photographiez bien éclairé, de face, avec tout le tableau dans le cadre. Un PDF du laboratoire donne le meilleur résultat.',
    },
    {
      q: 'Comment supprimer mes données ?',
      a: 'Dans « Mon espace → Données et consentements », vous pouvez supprimer les analyses enregistrées ou tout le compte avec les valeurs confirmées. Les copies des lignes publiques déjà téléchargées par d’autres ne peuvent pas être retirées.',
    },
    {
      q: 'Qui voit mes données ?',
      a: 'Vous seul, tant que la publication est désactivée. Si vous l’activez, vos lignes apparaissent dans le jeu de données public sous pseudonyme. Les laboratoires vérifiés ne voient que des statistiques agrégées, et seulement si vous avez consenti à l’utilisation pour la recherche.',
    },
  ],
  firstUpload: {
    title: 'Avant votre premier envoi',
    points: [
      'Il vous faut une analyse de sang avec neuf marqueurs, dont la CRP ultrasensible, et votre âge.',
      'Nous ne conservons pas le fichier original. Le texte ou l’image masquée est lu par le service de reconnaissance Google Gemini. Seules les valeurs que vous confirmez sont enregistrées.',
      'La publication est désactivée par défaut. Si vous l’activez, les lignes sont publiées sous pseudonyme et ne peuvent pas être retirées chez ceux qui les ont déjà téléchargées.',
    ],
    note: 'Ce résumé ne remplace pas les textes de consentement.',
    readGuide: 'Lire le guide complet',
    ok: 'Compris',
  },
};
