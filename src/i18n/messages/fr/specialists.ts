/** Rubrique pour médecins, chercheurs et laboratoires. Terminologie admise, faits sourcés. */
export const specialists = {
  kicker: 'Pour les spécialistes',
  title: 'Méthode, limites et données',
  lead: 'Pour les médecins, les chercheurs et les laboratoires : comment l’indice est calculé, où il ne doit pas être utilisé et comment accéder aux données.',
  audienceTitle: 'Qui êtes-vous ?',
  audiences: [
    {
      id: 'doctor',
      title: 'Médecin',
      body: 'Ce qu’est l’indice, jusqu’où s’y fier, ce qu’il n’est pas et comment en parler avec un patient qui vient avec ses valeurs.',
      action: 'Méthode et limites',
      page: 'method',
    },
    {
      id: 'researcher',
      title: 'Chercheur',
      body: 'Format des données, licences, liste des champs et téléchargement du jeu de données public.',
      action: 'Données et charte',
      page: 'data',
    },
    {
      id: 'laboratory',
      title: 'Laboratoire ou organisation',
      body: 'Accès aux statistiques agrégées par cohorte après vérification et accord d’utilisation des données.',
      action: 'Pour les laboratoires',
      page: 'labs',
    },
  ],
  pages: {
    method: 'Méthode',
    limits: 'Limites et bon usage',
    data: 'Données et charte',
    labs: 'Laboratoires et organisations',
    contact: 'Contact',
  },
  reviewBadge: 'Relecture médicale : {name}, {qualification}, {date}',

  method: {
    title: 'Méthode',
    lead: 'Âge phénotypique (PhenoAge) d’après Levine et al., Aging 2018;10(4):573–591. La formule s’exécute sur le serveur ; le navigateur ne calcule jamais l’indice.',
    formulaTitle: 'Formule',
    formulaBody: [
      'Étape 1. Un prédicteur linéaire xb est construit à partir de neuf marqueurs sanguins et de l’âge civil, avec les coefficients de Gompertz du tableau 1 de l’article. La protéine C réactive entre sous forme de logarithme népérien.',
      'Étape 2. xb est converti en M, la probabilité à 10 ans (120 mois) du modèle de Gompertz de l’article, gamma = 0,0076927.',
      'Étape 3. M est reconverti en années : PhenoAge = 141,50225 + ln(−0,00553 × ln(1 − M)) / 0,090165.',
      'Le moteur reproduit le cas détaillé des données supplémentaires de l’article (âge 71, PhenoAge 66,95) ; c’est un test unitaire du dépôt.',
    ],
    sourceTitle: 'D’où vient la formule',
    sourceBody:
      'Apprentissage : NHANES III, 9 926 adultes américains avec un bilan complet ; une régression de Cox pénalisée a retenu neuf marqueurs et l’âge parmi 42 candidats. Validation : NHANES IV, 6 209 adultes américains suivis jusqu’à 12 ans. Dans l’échantillon de validation, chaque année d’âge phénotypique au-delà de l’âge civil était associée à une probabilité de décès toutes causes confondues plus élevée de 9 % (HR 1,09).',
    unitsTitle: 'Unités et conversions',
    unitsLead:
      'Le dictionnaire conserve des unités courantes en laboratoire. Avant le calcul, trois marqueurs sont convertis dans les unités utilisées pour ajuster les coefficients.',
    colMarker: 'Marqueur',
    colLoinc: 'LOINC',
    colInput: 'Unité saisie',
    colModel: 'Unité du modèle',
    colCoefficient: 'Coefficient',
    conversions: {
      creatinine: 'mg/dl × 88,4 → µmol/l',
      glucose: 'mg/dl × 0,0555 → mmol/l',
      crp: 'mg/l × 0,1 → mg/dl, puis ln',
      same: 'sans conversion',
    },
    ageRow: 'Âge civil',
    versionsTitle: 'Versions',
    versions: [
      'Moteur : coefficients de Levine 2018, gamma 0,0076927, poids des PAL 0,0019 tel qu’imprimé.',
      'Dictionnaire des marqueurs : LOINC dictionary v1, licence CC BY 4.0.',
      'La version du lecteur est enregistrée avec chaque analyse lue.',
    ],
    pipelineTitle: 'Chaîne de traitement',
    pipeline: [
      {
        title: 'Réception en mémoire',
        body: 'Le fichier est lu dans la mémoire vive du serveur et n’est pas écrit sur disque. Un hachage SHA-256 est conservé pour la traçabilité.',
      },
      {
        title: 'Retrait des lignes personnelles',
        body: 'Pour un PDF texte, le texte est extrait sur le serveur avec pdfplumber et les lignes personnelles sont supprimées. Pour un scan ou une photo, un OCR local (Tesseract) masque ces lignes ; en cas de doute, la personne voit l’extrait masqué et décide de l’envoyer.',
      },
      {
        title: 'Reconnaissance',
        body: 'Le texte nettoyé ou l’image masquée est envoyé à un modèle de reconnaissance externe (Google Gemini), qui renvoie noms, valeurs et unités des marqueurs. Les noms sont associés au dictionnaire LOINC versionné ; les noms non reconnus restent dans une file à part.',
      },
      {
        title: 'Vérification humaine',
        body: 'La personne compare chaque valeur au compte rendu et corrige valeurs et unités. Rien n’est enregistré comme résultat avant cette confirmation.',
      },
      {
        title: 'Calcul',
        body: 'PhenoAge n’est calculé que si les neuf marqueurs et l’âge sont présents. Un marqueur manquant est signalé et jamais remplacé.',
      },
    ],
    slidersTitle: 'Sensibilité de l’algorithme',
    slidersLead:
      'Le même exemple fictif que sur la page d’accueil. Déplacez un marqueur pour voir la réaction de l’indice.',
  },

  limits: {
    title: 'Limites et bon usage',
    lead: 'Ce que l’indice n’est pas, ce qui fausse les valeurs et ce que l’on sait de son domaine d’application.',
    notTitle: 'Ce que l’indice n’est pas',
    notItems: [
      'Pas un diagnostic. Il ne nomme ni n’exclut aucune maladie.',
      'Pas une prévision pour une personne donnée. Les coefficients décrivent une moyenne de population, pas un individu.',
      'Pas une raison de commencer, d’arrêter ou de modifier un traitement.',
      'Pas un substitut aux marqueurs eux-mêmes. Chaque marqueur s’interprète selon l’intervalle de référence de son laboratoire.',
    ],
    authorsNote:
      'Les auteurs de la formule écrivent qu’une telle estimation ne doit pas remplacer les marqueurs cliniques dans les décisions médicales.',
    distortTitle: 'Ce qui fausse les valeurs',
    distortItems: [
      'Une infection ou une inflammation aiguë : la protéine C réactive et les leucocytes montent en quelques jours.',
      'Un effort physique intense la veille de l’analyse.',
      'Une analyse faite sans être à jeun : la glycémie augmente.',
      'Des laboratoires, méthodes et unités différents d’une analyse à l’autre. Comparez des analyses faites dans les mêmes conditions.',
      'Une CRP standard au lieu d’une CRP ultrasensible : les faibles valeurs peuvent être notées « inférieur au seuil » et ne permettent pas un calcul exact.',
    ],
    populationTitle: 'Population et applicabilité',
    populationBody: [
      'La formule a été établie et validée sur des enquêtes nationales américaines (NHANES III et NHANES IV). Sa précision dans d’autres populations n’a pas été établie par cette plateforme.',
      'Les auteurs notent que des marqueurs comme la CRP, l’albumine, la créatinine et la glycémie varient peu chez les enfants, les jeunes adultes et les personnes en très bonne santé ; l’indice peut donc moins bien les distinguer.',
      'L’applicabilité selon les stades de la ménopause et dans d’autres groupes particuliers n’est pas revendiquée ici. Cette partie sera complétée par le relecteur médical, références à l’appui.',
    ],
    patientTitle: 'Si un patient vient avec ses valeurs',
    patientItems: [
      'L’indice est une mesure de recherche. Il est raisonnable de regarder les neuf marqueurs eux-mêmes et leurs intervalles de référence.',
      'Un grand écart entre l’indice et l’âge civil invite à revoir chaque marqueur ; ce n’est pas une conclusion en soi.',
      'La plateforme ne donne aucun conseil aux patients. Les décisions cliniques restent celles du médecin.',
    ],
  },

  data: {
    title: 'Données et charte',
    lead: 'Contenu du jeu de données public, licences de publication et organisation de l’accès.',
    licensesTitle: 'Licences',
    licenses: [
      { name: 'AGPL-3.0', body: 'Code source de la plateforme.' },
      { name: 'CC BY 4.0', body: 'Dictionnaire de correspondance LOINC.' },
      { name: 'CC0 1.0', body: 'Lignes du jeu de données public et statistiques agrégées.' },
    ],
    fieldsTitle: 'Champs du jeu de données public',
    fieldsShown: [
      'ID public pseudonyme',
      'Date du prélèvement',
      'Âge au prélèvement, s’il figure sur le compte rendu',
      'Code LOINC, nom du marqueur et nom tel qu’imprimé',
      'Valeur, unité et statut de correspondance',
    ],
    fieldsHidden: [
      'Nom et e-mail',
      'Date de naissance',
      'ID interne du compte',
      'Hachage du document original',
      'Entrées du journal',
    ],
    shownLabel: 'Publié',
    hiddenLabel: 'Jamais publié',
    pseudonymNote:
      'Les lignes sont pseudonymisées, pas anonymes : un même ID public relie toutes les lignes d’une personne. Seules les statistiques agrégées sont anonymes.',
    cc0Note:
      'Les lignes sont publiées sous CC0. Les copies déjà téléchargées par d’autres ne peuvent pas être retirées, même si le participant supprime ensuite son compte.',
    accessTitle: 'Modèle d’accès',
    access: [
      {
        title: 'Jeu de données public',
        body: 'Lignes des participants qui ont activé la publication. API en lecture seule GET /api/v1/dataset, plus CSV, Parquet et fiche descriptive.',
      },
      {
        title: 'Niveau 1 : agrégats pour laboratoires vérifiés',
        body: 'Uniquement pour les participants ayant consenti à l’utilisation pour la recherche. Groupes de moins de 10 masqués, effectifs arrondis au multiple de 5 inférieur, adultes seulement.',
      },
      {
        title: 'Niveau 2 : données individuelles pour une étude précise',
        body: 'Prévu. Uniquement pour les participants qui acceptent explicitement cette étude. Non disponible aujourd’hui.',
      },
    ],
  },

  labs: {
    title: 'Laboratoires et organisations',
    lead: 'Les organisations vérifiées peuvent demander des statistiques agrégées sur les cohortes de participants consentants. Les données individuelles ne sont pas accessibles.',
    steps: [
      'Enregistrez l’organisation et confirmez l’e-mail du responsable du compte.',
      'Notre équipe vérifie l’organisation manuellement.',
      'Acceptez l’accord d’utilisation des données une fois approuvé juridiquement.',
    ],
    privacy:
      'Les comptes de laboratoire sont séparés des comptes des participants. Les petits groupes sont masqués et les effectifs arrondis.',
    open: 'Ouvrir le portail des laboratoires',
  },

  contact: {
    title: 'Contact',
    lead: 'Questions sur la méthode, les données ou une collaboration :',
  },
};
