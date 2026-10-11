export const shell = {
  documentTitle: '{brand} : âge biologique à partir d’analyses de sang, pour la recherche',
  disclaimer:
    'PhenoAge est un indice de recherche (Levine et al., Aging 2018). Ce n’est ni un service médical, ni un diagnostic, ni une recommandation de traitement.',
  dataDisclaimer:
    'Un outil d’auto-observation à des fins de recherche. Il ne pose aucun diagnostic, ne remplace pas un médecin et ne donne aucun conseil de traitement.',
  splashAria: '{brand}. Cliquez pour continuer.',
  researchProtocol: 'Projet de recherche',
  tutorialExample: 'Exemple fictif',
  notPatientPanel: 'Pas les données d’un patient • coefficients de Levine 2018',
  levineWeights: 'Coefficients de Levine 2018',
  exampleBanner:
    'Vous voyez un exemple fictif : Alexeï, 45 ans. Envoyez votre propre analyse pour voir vos valeurs.',
  sampleBanner:
    'Vous voyez un échantillon fictif. Envoyez votre propre analyse pour voir vos valeurs.',
  exampleBannerAction: 'Envoyer une analyse',
  footerBrand: '{brand}',
  footerNonDiagnostic:
    'Un outil d’auto-observation et de recherche. Il ne pose aucun diagnostic, ne remplace pas un médecin et ne donne aucun conseil de traitement.',
  footerCitation: 'PhenoAge : Levine et al., Aging 2018',
  footerNoRawFiles: 'Les fichiers originaux des analyses ne sont pas conservés',
  footerLoinc: 'Dictionnaire LOINC v1',
  footerGuide: 'Guide de l’utilisateur',
  footerSpecialists: 'Pour les spécialistes',
  footerCharter: 'Charte des données',
  footerConsent: 'Texte du consentement',
  footerContact: 'Contact',
  footerLicensesTitle: 'Licences',
  footerLicenses: 'Code AGPL-3.0 · dictionnaire des marqueurs CC BY 4.0 · jeu de données public CC0',
  phenoAgeFailed: 'Le calcul de l’indice a échoué',
  couldNotCreateAccount: 'Impossible de créer le compte',
  couldNotSignIn: 'Connexion impossible',
  extractionFailed: 'La lecture de l’analyse a échoué',
  confirmFailed: 'La confirmation a échoué',
  confirmRejected:
    'Le texte ressemble à un nom ou à un numéro de téléphone : il n’a pas été enregistré.',
  unknownLaboratory: 'Laboratoire non indiqué',
  years: 'ans',
  yrs: 'ans',
  apiErrors: {
    invalidCredentials: 'E-mail ou mot de passe incorrect, ou adresse pas encore confirmée.',
    linkExpired:
      'Ce lien a expiré ou a déjà été utilisé. Connectez-vous avec votre e-mail et votre mot de passe, ou demandez un nouveau lien.',
    rateLimited: 'Trop de tentatives. Patientez 15 minutes puis réessayez.',
    invalidEmail: 'Vérifiez l’adresse e-mail.',
    consentMissing: 'Le consentement au traitement des données de santé est requis.',
    consentOutdated:
      'Le texte du consentement a été mis à jour. Rechargez la page et confirmez à nouveau.',
    invalidPhrase: 'La phrase de récupération est incorrecte.',
    notSignedIn: 'Votre session a expiré. Reconnectez-vous.',
    healthConsentRequired:
      'Pour téléverser des analyses, activez le consentement aux données de santé dans Compte → Données et consentements.',
    labConfirmRequired: 'Confirmez d’abord l’adresse e-mail du laboratoire.',
    dataAccessClosed: 'L’accès aux données n’est pas encore ouvert pour cette organisation.',
    unsupportedFile:
      'Ce format de fichier n’est pas pris en charge. Utilisez PDF, PNG, JPG ou TIFF.',
    fileTooLarge: 'Le fichier dépasse 15 Mo.',
    emptyFile: 'Le fichier est vide.',
    unreadableImage: 'L’image n’a pas pu être lue. Utilisez une photo plus nette ou un PDF.',
    noMarkers: 'Aucun résultat chiffré n’a été trouvé dans ce fichier.',
    sessionExpired: 'La session de téléversement a expiré. Téléversez à nouveau le fichier.',
    recognitionUnavailable:
      'La lecture des comptes rendus est temporairement indisponible. Réessayez plus tard.',
    recognitionTimeout:
      'La lecture a pris trop de temps. Réessayez ou recadrez la photo sur le tableau des résultats.',
    recognitionFailed:
      'Le compte rendu n’a pas pu être lu. Réessayez ou téléversez un fichier plus net.',
    serverUnavailable: 'Le serveur ne répond pas. Réessayez dans quelques minutes.',
  },
};
