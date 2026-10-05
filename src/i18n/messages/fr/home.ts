/** Page d’accueil pour un nouveau participant. Aucun terme technique ici. */
export const home = {
  kicker: 'Recherche ouverte sur l’âge biologique',
  headline: 'Transformez vos résultats d’analyses de sang en données biologiques.',
  headlineAccent: 'Aidez la science à comprendre le vieillissement.',
  subhead:
    'Envoyez une analyse, vérifiez les valeurs et découvrez votre indice d’âge biologique. Si vous le souhaitez, partagez vos données sans nom ni e-mail pour aider les scientifiques à mieux comprendre comment vieillit l’organisme.',
  ctaCreate: 'Créer un compte',
  ctaUpload: 'Envoyer une analyse',
  ctaHow: 'Comment ça marche',
  trustLine: 'Nous ne conservons pas le fichier original.',
  trustLink: 'Détails dans le guide',

  missionKicker: 'Notre mission',
  missionTitle: 'Une base de données ouverte sur l’âge biologique',
  missionBody: [
    'Nous construisons une base de données ouverte sur l’âge biologique. Les scientifiques du monde entier pourront y vérifier ce qui ralentit vraiment le vieillissement : alimentation, médicaments, habitudes.',
    'Nous voulons que la médecine apprenne non seulement à soigner les maladies, mais aussi à repérer tôt l’usure de l’organisme.',
    'Les données que les participants choisissent de partager sont publiées sous pseudonyme, sans nom ni coordonnées.',
  ],
  missionStatus:
    'La base commence tout juste à se remplir : vous pouvez faire partie des premiers participants.',

  indexKicker: 'L’indice',
  indexTitle: 'Qu’est-ce que l’indice de Levine (PhenoAge)',
  indexBody: [
    'L’indice de Levine compare votre analyse de sang aux données de milliers de personnes et indique à quel âge vos valeurs correspondent en moyenne. La date de naissance compte les années vécues ; l’indice tient compte de l’état de l’organisme.',
    'La formule a été publiée en 2018 dans la revue Aging par Morgan Levine, Steve Horvath et leurs coauteurs. Elle a été construite à partir des données d’environ dix mille adultes d’une enquête nationale de santé aux États-Unis, puis vérifiée sur un autre groupe de six mille personnes.',
    'La formule utilise l’âge et neuf marqueurs sanguins. Ensemble, ils reflètent l’inflammation, le foie et les reins, le métabolisme et l’immunité. C’est un indice de recherche, pas un diagnostic.',
  ],
  markersToggle: 'Quels marqueurs sont utilisés',
  markersNote:
    'Les neuf sont nécessaires. S’il en manque un, l’indice n’est pas calculé et nous indiquons lequel manque.',
  paperLink: 'Article original (Aging, 2018)',
  matrixLink: 'Tableau complet des marqueurs pour les spécialistes',

  forYouKicker: 'Pour vous',
  forYouTitle: 'Pourquoi c’est utile pour vous',
  forYou: [
    {
      title: 'Voir l’écart',
      body: 'L’indice montre de combien votre âge biologique s’écarte de votre âge civil, et comment cet écart évolue.',
    },
    {
      title: 'Remarquer un changement',
      body: 'La formule comprend des marqueurs de l’inflammation et du métabolisme : un changement net entre deux analyses est une raison d’en parler avec un médecin. L’indice ne pose pas de diagnostic.',
    },
    {
      title: 'Observer votre mode de vie',
      body: 'Vous avez changé d’alimentation ou commencé à courir ? Vous pouvez refaire une analyse dans trois mois environ et comparer. Gardez les mêmes conditions : à jeun, sans maladie ni gros effort la veille, car l’inflammation et les leucocytes changent vite.',
    },
  ],

  forScienceKicker: 'Pour la science',
  forScienceTitle: 'Pourquoi c’est utile pour la science',
  forScienceLead: 'Pour comprendre le vieillissement, les scientifiques ont besoin de grands ensembles de données humaines.',
  forScience: [
    {
      title: 'Tester des hypothèses plus vite',
      body: 'Personne ne peut attendre 40 ans pour savoir si un régime ou un médicament ralentit le vieillissement. Les indices d’âge biologique donnent un premier signal en quelques mois. Leur capacité à remplacer de vrais critères de santé est encore à l’étude.',
    },
    {
      title: 'Chercher des régularités',
      body: 'En comparant de nombreux profils, on peut chercher ce qu’ont en commun les personnes dont l’âge biologique est inférieur à l’âge civil : mode de vie, alimentation, habitudes.',
    },
    {
      title: 'Trouver de nouveaux marqueurs',
      body: 'Un jeu de données ouvert permet de tester de nouvelles idées sur les premiers signes du vieillissement sans collecter ses propres données de zéro.',
    },
  ],

  example: {
    badge: 'Exemple fictif',
    title: 'Alexeï, 45 ans',
    storyStart: [
      'Alexeï a 45 ans, il travaille beaucoup et dort peu. Il a envoyé une analyse de sang récente. La protéine C réactive et la glycémie dépassent l’intervalle de référence imprimé sur le compte rendu, et la créatinine est proche de la limite haute de son intervalle.',
      'L’indice de Levine indiquait 51 ans, soit 6 ans de plus que son âge civil. Alexeï n’a pas cherché les causes seul : il a montré les valeurs à son médecin, qui a prescrit des examens et établi avec lui un plan pour le sommeil, l’alimentation et l’activité.',
    ],
    storyFollowUp: [
      'Quatre mois plus tard, il a refait l’analyse. La protéine C réactive est passée de 7,0 à 3,0 mg/l, et les autres marqueurs se sont rapprochés du milieu de leurs intervalles de référence. L’indice : 47 ans.',
      'Alexeï a obtenu une évolution claire à discuter avec son médecin, et la science un point de données de plus, s’il a activé la publication.',
    ],
    footnote:
      'Exemple fictif. Les valeurs sont calculées avec la formule de Levine 2018 sur notre serveur. Votre résultat sera différent.',
    startTab: 'Première analyse',
    followUpTab: '4 mois plus tard',
    passportAge: 'Âge civil',
    indexAge: 'Indice de Levine',
    difference: 'Écart',
    years: 'ans',
    calculating: 'Calcul…',
    unavailable: 'L’indice n’a pas pu être calculé pour le moment.',
    slidersTitle: 'Essayez vous-même',
    slidersLead: 'Déplacez un marqueur : le serveur recalcule l’indice.',
    crpLabel: 'Protéine C réactive (CRP)',
    albuminLabel: 'Albumine',
    reset: 'Revenir aux valeurs d’Alexeï',
  },

  howKicker: 'Étape par étape',
  howTitle: 'Comment ça marche',
  howSteps: [
    {
      title: 'Envoyez une analyse',
      body: 'Un PDF, un scan ou une photo du compte rendu.',
    },
    {
      title: 'Vérifiez les valeurs',
      body: 'Nous lisons les marqueurs, vous confirmez ou corrigez.',
    },
    {
      title: 'Obtenez l’indice',
      body: 'Puis décidez si vous partagez vos données avec la science.',
    },
  ],
  privacyTitle: 'Ce qui arrive à vos données',
  privacyLines: [
    'Nous ne conservons pas le fichier original. Seules les valeurs confirmées sont enregistrées.',
    'Les lignes contenant votre nom sont masquées avant la lecture des valeurs.',
    'Le partage avec la science reste désactivé tant que vous ne l’activez pas.',
  ],
  guideLink: 'Lire le guide complet',

  finalTitle: 'Envie de connaître votre indice ?',
  finalBody: 'Il vous faut une analyse de sang avec neuf marqueurs et environ cinq minutes.',
  specialistsPrompt: 'Vous êtes médecin ou chercheur ?',
  specialistsLink: 'Aller à la rubrique pour les spécialistes',
};
