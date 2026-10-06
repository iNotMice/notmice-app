/** Guide de l’utilisateur. Une page avec des ancres, à lire avant le premier envoi. */
export const instructions = {
  stage: 'Guide',
  title: 'Guide de l’utilisateur',
  lead: 'Un guide pas à pas : créer un compte, donner les consentements, envoyer une analyse, vérifier les valeurs et retrouver vos résultats. Si quelque chose ne marche pas, voyez la rubrique « Si quelque chose ne marche pas ».',
  tocTitle: 'Sur cette page',
  sections: {
    start: 'Démarrage rapide',
    account: 'Compte et connexion',
    consents: 'Consentements',
    need: 'Ce qu’il vous faut',
    upload: 'Comment envoyer',
    file: 'Ce qui arrive au fichier',
    check: 'Vérifier les valeurs',
    get: 'Ce que vous obtenez',
    share: 'Partager vos données',
    cabinet: 'Mon espace',
    trouble: 'Si quelque chose ne marche pas',
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
  start: {
    lead: 'Six étapes de la première visite au résultat. Chaque étape est détaillée plus bas sur cette page.',
    steps: [
      {
        title: 'Créez un compte',
        body: 'Cliquez sur « Invité » en haut à droite de la page (sur téléphone, en bas du menu), puis sur « Créer un compte ». Saisissez votre e-mail et un mot de passe d’au moins 12 caractères.',
      },
      {
        title: 'Cochez les consentements',
        body: 'Dans le même formulaire, cochez le consentement obligatoire au traitement des données de santé. Les deux autres sont facultatifs et peuvent être donnés plus tard.',
      },
      {
        title: 'Confirmez votre e-mail',
        body: 'Ouvrez l’e-mail et cliquez sur le lien. Sans cela, la connexion est impossible. Connectez-vous ensuite avec le même e-mail et le même mot de passe.',
      },
      {
        title: 'Envoyez une analyse',
        body: 'Menu « Envoi → Envoyer une analyse », bouton « Choisir un fichier ». Un PDF, un scan ou une photo du compte rendu convient.',
      },
      {
        title: 'Vérifiez les valeurs',
        body: 'Comparez chaque valeur et chaque unité au compte rendu, corrigez les erreurs et cliquez sur « Tout confirmer et calculer PhenoAge ».',
      },
      {
        title: 'Consultez vos résultats',
        body: 'L’indice, toutes vos analyses et les graphiques des marqueurs se trouvent dans le menu « Mon espace ».',
      },
    ],
    languageNote: 'La langue du site se change avec le sélecteur dans l’en-tête, à côté du bouton de connexion.',
  },
  account: {
    lead: 'Un compte permet d’enregistrer vos analyses et d’en voir l’historique. À la place d’un nom, le compte a un ID public pseudonyme.',
    steps: [
      'Cliquez sur « Invité » en haut à droite de la page. Sur téléphone, ouvrez le menu : le bouton de connexion est en bas.',
      'Dans la fenêtre de connexion, cliquez sur « Créer un compte ».',
      'Saisissez votre adresse e-mail et un mot de passe d’au moins 12 caractères. Tapez le mot de passe deux fois.',
      'Cochez le consentement obligatoire au traitement des données de santé. Sans lui, le compte ne peut pas être créé. Les autres consentements sont facultatifs.',
      'Cliquez sur « Créer un compte ». Un e-mail avec un lien arrive. Le lien ne sert qu’une fois et reste valable 24 heures 30 minutes.',
      'Ouvrez l’e-mail et cliquez sur le lien. Si l’e-mail n’arrive pas, regardez dans les dossiers Spam et Promotions.',
      'Revenez sur le site, cliquez sur « Invité » et connectez-vous avec le même e-mail et le même mot de passe. « Invité » devient « Connecté » ; ce bouton ouvre votre espace.',
    ],
    forgot:
      'Mot de passe oublié ? Dans la fenêtre de connexion, cliquez sur « Mot de passe oublié ? », saisissez votre e-mail et ouvrez le lien reçu. Le mot de passe se change aussi dans « Mon espace → Connexion et sécurité ».',
    phrase:
      'Votre compte a été créé avec une phrase de 12 mots ? Connectez-vous avec elle : dans la fenêtre de connexion, cliquez sur « Se connecter avec une phrase de récupération ».',
  },
  consents: {
    lead: 'Un consentement s’applique dès que vous le cochez. Vous pouvez modifier chacun d’eux à tout moment : « Mon espace → Données et consentements », bloc « Vos consentements » en haut de la page.',
    items: [
      {
        title: 'Traitement des données de santé',
        badge: 'Obligatoire',
        body: 'Sans lui, le serveur n’accepte pas les fichiers d’analyses. Si vous le décochez, les nouveaux envois s’arrêtent.',
      },
      {
        title: 'Utilisation pour la recherche',
        badge: 'Facultatif',
        body: 'Vos analyses confirmées et vos réponses au questionnaire entrent dans des statistiques globales pour les laboratoires vérifiés. Les laboratoires ne voient que des totaux par groupe, jamais les données d’une personne. Les groupes de moins de 10 sont masqués.',
      },
      {
        title: 'Questionnaire',
        badge: 'Facultatif',
        body: 'Autorise la conservation de vos réponses : sexe à la naissance, année de naissance, pays, taille, poids, tabac, alcool et activité. Tant que ce consentement n’est pas coché, les champs du questionnaire restent inactifs.',
      },
      {
        title: 'Publication dans le jeu de données ouvert',
        badge: 'Choix séparé',
        body: 'C’est un interrupteur à part, désactivé par défaut. Voir la rubrique « Partager vos données ».',
      },
    ],
    surveyNote:
      'Le questionnaire se trouve sur la même page, sous les consentements. Toutes les questions sont facultatives. Remplissez ce que vous voulez et cliquez sur « Enregistrer les réponses ».',
  },
  cabinet: {
    lead: 'Le menu « Mon espace » fonctionne une fois connecté. Il compte six rubriques, visibles par vous seul.',
    items: [
      {
        title: 'Résumé',
        body: 'Votre compte, le nombre d’analyses, le dernier indice et ce qui manque pour le calculer, les dernières valeurs des marqueurs. Vous pouvez aussi y télécharger votre copie en JSON ou CSV.',
      },
      {
        title: 'Mes analyses',
        body: 'Toutes les analyses confirmées, les plus récentes en haut. « Afficher les valeurs » ouvre le tableau. Une analyse erronée peut être supprimée puis envoyée à nouveau.',
      },
      {
        title: 'Marqueurs',
        body: 'Les graphiques de chaque marqueur et de l’indice dans le temps. Utiles dès que vous avez plus d’une analyse.',
      },
      {
        title: 'Journal',
        body: 'Des notes sur les médicaments, l’alimentation, l’activité et le sommeil, avec dates de début et de fin. Vous seul les voyez ; elles ne sont jamais transmises aux laboratoires.',
      },
      {
        title: 'Données et consentements',
        body: 'Consentements, questionnaire, publication, téléchargement de votre copie, suppression des analyses et du compte.',
      },
      {
        title: 'Connexion et sécurité',
        body: 'Changer le mot de passe, se déconnecter des autres appareils ou se déconnecter.',
      },
    ],
  },
  trouble: [
    {
      q: 'Un message sur le consentement aux données de santé s’affiche à l’envoi',
      a: 'Le compte n’a pas de consentement obligatoire en vigueur. Ouvrez « Mon espace → Données et consentements », cochez le consentement obligatoire au traitement des données de santé et renvoyez le fichier.',
    },
    {
      q: 'L’e-mail avec le lien n’arrive pas',
      a: 'Attendez quelques minutes et regardez dans les dossiers Spam et Promotions. Vérifiez l’orthographe de l’adresse. Pour recevoir un nouveau lien, créez à nouveau le compte avec la même adresse : tant que l’e-mail n’est pas confirmé, le message est renvoyé.',
    },
    {
      q: 'Le lien de l’e-mail ne s’ouvre pas',
      a: 'Le lien ne sert qu’une fois et reste valable 24 heures 30 minutes. S’il a expiré ou a déjà servi, demandez-en un nouveau comme lors de la première inscription.',
    },
    {
      q: 'Les champs du questionnaire sont grisés',
      a: 'Le questionnaire s’ouvre dès que vous cochez « Questionnaire (facultatif) » dans le bloc « Vos consentements » de « Mon espace → Données et consentements ».',
    },
    {
      q: 'L’indice n’a pas été calculé',
      a: 'L’indice demande les neuf marqueurs et votre âge sur un même compte rendu. Ce qui manque est indiqué dans « Mon espace → Résumé » et dans « Mes analyses ». Les autres valeurs restent enregistrées.',
    },
    {
      q: 'Une valeur a été mal lue',
      a: 'Corrigez-la sur l’écran de vérification avant de confirmer. Si l’analyse est déjà confirmée avec une erreur, supprimez-la dans « Mon espace → Mes analyses » et envoyez-la à nouveau.',
    },
    {
      q: 'Mon espace me demande de me connecter',
      a: 'Vous n’êtes pas connecté ou la session a expiré. Cliquez sur « Invité » en haut à droite et reconnectez-vous.',
    },
    {
      q: 'J’ai oublié mon mot de passe',
      a: 'Dans la fenêtre de connexion, cliquez sur « Mot de passe oublié ? », saisissez votre e-mail et ouvrez le lien reçu. Le lien n’est envoyé que si l’e-mail du compte est confirmé.',
    },
  ],
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
