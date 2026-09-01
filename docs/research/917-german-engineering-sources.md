# Sources d'ingénierie allemandes — moteur Porsche 917

## Périmètre

Cette note recense uniquement des pages germanophones consultées le 1er septembre
2026. Elle sépare les faits publiés, les hypothèses de reconstruction et les
données toujours absentes. Aucun texte, dessin, photographie, PDF ou maillage de
ces éditeurs n'est copié dans le dépôt.

Niveaux de preuve employés : **A** = publication Porsche ou donnée constructeur ;
**B** = spécialiste ou ingénieur identifié ; **C** = source technique secondaire
non corroborée ; **D** = piste à vérifier. Une valeur publiée n'est pas pour
autant une cote de fabrication.

## Matrice des claims

| Claim paraphrasé | Variante | Valeur / unité | Source | Niveau | Droits | Usage autorisé dans le twin | Contradictions ou réserve |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Architecture moteur déclarée | 917/30 | V à 180°, 12 cylindres, turbo, 5 374 cm³ | [Porsche Museum](https://newsroom.porsche.com/de/pressemappen/Porsche-Museum/Porsche-917-30-Spyder.html) | A | Copyright Porsche, référence uniquement | Arbre USD, BOM et enveloppe fonctionnelle | « V à 180° » ne suffit pas à prouver une cinématique boxer ; conserver la topologie publiée |
| Première cylindrée de série | 917, 1969 | 4 494 cm³ ; alésage 85 mm ; course 66 mm ; 580 PS | [auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/), corroboration de la cylindrée et de la puissance par [Porsche](https://newsroom.porsche.com/de/2019/unternehmen/porsche-917-50-jahre-goodwood-members-meeting-2019-17461.html) | B pour les cotes, A pour cylindrée/puissance | Copyright, référence uniquement | Contrôle d'échelle des cylindres et paramètre de course | Ne pas mélanger avec le 5 litres ni avec le 917/30 |
| Évolution atmosphérique | 917 5 litres | 4 999 cm³ ; 86,8 × 70,4 mm ; compression 10,5:1 ; 630 PS à 8 300 min⁻¹ | [auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/) | B | Copyright, référence uniquement | Paramètres piston, course et premier cas de charge | Donnée secondaire ; les détails de chambre restent inconnus |
| Évolution Can-Am | 917/30, 1973 | 5 374 cm³ ; 90 × 70,4 mm ; compression 6,5:1 ; 1 100 PS à 7 800 min⁻¹ ; 112 mkg à 6 400 min⁻¹, soit environ 1 098 N·m | [auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/) | B | Copyright, référence uniquement | Paramètres piston/course et charge mécanique | Puissance dépendante du boost et du réglage ; la conversion en N·m est calculée, non citée |
| Puissance de course et version record | 917/30 | 1 100 PS à 7 800 min⁻¹ ; version record 1975 avec échangeurs : 1 230 PS | [Porsche, « Am Limit »](https://newsroom.porsche.com/de/motorsport/porsche-919-hybrid-evo-917-30-canam-spyder-timo-bernhard-mark-donohue-rennwagen-16319.html) | A | Copyright Porsche, référence uniquement | Séparer les profils de charge 1973 et 1975 | D'autres pages Porsche indiquent 1 200 PS ou « plus de 1 200 PS » ; ne pas fusionner les réglages |
| Goujons de culasse | Moteur 917 présenté pour 1970 | 48 pièces ; longueur 149,5 mm ; tige Ø 9 mm ; masse 65 g par pièce | [Porsche Christophorus](https://christophorus.porsche.com/de/2019/390/le-mans-1970-hans-mezger-17024.html) | A | Copyright Porsche, référence uniquement | Meilleur contrôle d'échelle public ; interface carter–cylindre–culasse et masse BOM | Vérifier physiquement avant extension au 917/30 |
| Matériau et isolation des goujons | 917 | Alliage d'acier Dilavar ; gaine isolante en fibre de verre et résine | [Porsche Christophorus](https://christophorus.porsche.com/de/2019/390/le-mans-1970-hans-mezger-17024.html) | A | Copyright Porsche, référence uniquement | Modèle thermo-mécanique et dilatations relatives | Nuance, propriétés et procédé exacts non publiés |
| Carter, cylindres et bielles | 917 | Carter en magnésium moulé au sable ; cylindres individuels revêtus Nikasil ; bielles en titane | [auto motor und sport, entretien Hans Mezger](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/) | B | Copyright, référence uniquement | Affectations de matériau provisoires, masse et thermique | Alliages, traitements et géométries non publiés ; aucune matière ne doit être libérée pour fabrication sur cette seule source |
| Distribution et allumage | Type 912 / 917 | Deux arbres à cames par rangée ; deux soupapes inclinées et deux bougies par cylindre ; entraînement central par engrenages | [auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/) | B | Copyright, référence uniquement | Cinématique des arbres, soupapes, engrenages et allumage | Le Type 922 à quatre soupapes est un concept distinct et ne doit pas remplacer la configuration historique |
| Vilebrequin et sortie de puissance | 917 | Huit paliers lisses ; prise de puissance centrale | [auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/) | B | Copyright, référence uniquement | Décomposition du vilebrequin, des demi-carters et de la transmission | Longueurs, diamètres et déports restent inconnus |
| Ordre d'allumage déclaré | 917 | 1-9-5-12-3-8-6-10-2-7-4-11 | [auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/) | B | Fait technique cité ; article protégé | Animation, excitation cylindre et acoustique | La convention de numérotation doit être confirmée par un dessin d'origine |
| Lubrification | 917 | Carter sec ; une pompe de pression et six pompes de récupération ; charge annoncée de 24 l | [auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/) | B | Copyright, référence uniquement | Schéma fonctionnel d'huile, thermique et BOM | Le réservoir de 55 l publié pour une 917 KH correspond à un composant/une variante de véhicule distincts |
| Refroidissement par air | 917 | Débit de ventilateur annoncé : 3 100 l/s | [auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/) | B | Copyright, référence uniquement | Première condition limite volumique pour une étude de sensibilité | Courbe pression–débit, régime, fuites et répartition par cylindre absents |
| Entraxe et diamètres de soupapes candidats | Type 912 | Entraxe cylindres 118 mm ; admission Ø 47,5 mm ; échappement Ø 40,5 mm | [Kfz-tech](https://www.kfz-tech.de/Buchprojekte/Porsche/917Teil2.htm) | C | Copyright, référence uniquement | Hypothèses de contrôle d'échelle et de reconstruction de culasse | Aucune corroboration primaire trouvée : ne pas verrouiller la CAO sur ces valeurs |
| Calage de distribution candidat | Type 912 | Admission : ouverture 104° avant PMH, fermeture 104° après PMB ; échappement : ouverture 105° avant PMB, fermeture 75° après PMH | [Kfz-tech](https://www.kfz-tech.de/Buchprojekte/Porsche/917Teil2.htm) | C | Copyright, référence uniquement | Première animation paramétrique des soupapes | Convention et jeu de contrôle non publiés ; impropre à une validation de collision définitive |
| Injection mécanique | 917 | Système Bosch ; pression publiée par la source secondaire : 17,5 bar | [auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/) et [Kfz-tech](https://www.kfz-tech.de/Buchprojekte/Porsche/917Teil2.htm) pour la pression | B pour l'architecture, C pour la pression | Copyright, référence uniquement | BOM carburant et modèle 1D initial | Came de pompe, débits et loi régime/charge inconnus |
| Suralimentation historique | 917/10 et 917/30 | Deux turbocompresseurs avec soupape de dérivation ; fournisseur historiquement attribué à Eberspächer | [Porsche, « Turbo-Vision »](https://newsroom.porsche.com/de/2024/historie/porsche-turbotechnologie-motorenbau-vision-christophorus-411-36722.html) pour l'architecture ; [Classic Driver](https://www.classicdriver.com/de/article/porsche-sound-nacht-m%C3%A4nner-motoren-manierismen) pour Eberspächer | A pour l'architecture, B pour le fournisseur | Copyright, référence uniquement | Nomenclature turbo, collecteurs et commande de boost | Aucune preuve allemande crédible trouvée pour KKK/K26 ; modèle et cartes du turbo Eberspächer inconnus |
| Pression de suralimentation publiée | 917/30 | 1,3 bar | [auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/) | B | Copyright, référence uniquement | Point d'essai exploratoire uniquement | Pression absolue ou relative non précisée : ne pas l'utiliser comme condition limite définitive |
| Réponse transitoire et panne documentée | Prototypes turbo 1971–1972 | Environ une seconde avant la montée de puissance ; essai du 27 octobre 1971 interrompu par des soupapes restées pendues | [Porsche, « Mission 917 »](https://christophorus.porsche.com/de/2021/401/weissach-917.html) | A | Copyright Porsche, référence uniquement | Cible qualitative de spool et scénario FMEA | Compte rendu historique, pas une courbe instrumentée |
| Commande de boost par le pilote | 917/30 | Boost augmenté au départ puis réduit pour la durée moteur et la consommation | [Porsche, « Am Limit »](https://newsroom.porsche.com/de/motorsport/porsche-919-hybrid-evo-917-30-canam-spyder-timo-bernhard-mark-donohue-rennwagen-16319.html) | A | Copyright Porsche, référence uniquement | Contrôleur de mission dans Omniverse | Positions de commande et pressions associées inconnues |
| Validation contemporaine d'un moteur recréé | Réplique fonctionnelle 917 | EGT et température de culasse par cylindre ; arrêt automatique rapide ; cartographie du besoin en carburant sur banc | [Herrmann Motorenentwicklung](https://herrmann-motorenentwicklung.de/porsche-917-eine-ikone-des-motorsports-auf-unserem-pruefstand/) | B | Copyright, référence uniquement ; collaboration requise | Architecture d'instrumentation, banc et plan de corrélation | Aucune série de mesures numériques n'est publiée |
| Méthode Porsche de reconstruction | 917-001 | Démontage, scan 3D, reconstruction surfacique et comparaison aux dessins de construction avant réalisation d'outillages | [Porsche Museum](https://newsroom.porsche.com/de/2019/historie/porsche-917-001-rueckbau-restaurierung-museum-17524.html) | A | Copyright Porsche, référence uniquement | Justifie la chaîne scan → surfaces → cotes d'origine → contrôle | La page concerne principalement la carrosserie ; elle valide une méthode, pas les dimensions du moteur |
| Référence Porsche de validation additive | Piston moderne de 911 GT2 RS | LMF/LPBF en alliage d'aluminium ; masse réduite de 10 % ; canal de refroidissement fermé ; essai moteur de 200 h | [Porsche Newsroom](https://newsroom.porsche.com/de/2020/technik/porsche-kooperation-mahle-trumpf-kolben-3d-drucker-leistung-effizienz-911-gt2-rs-21461.html) | A | Copyright Porsche, référence uniquement | Modèle de qualification pour une future pièce imprimée | Ne démontre ni la fabricabilité ni la sécurité d'un piston 917 |

## Contradictions à conserver comme variantes

- La puissance du 917/30 apparaît selon les pages Porsche à 1 100 PS,
  1 200 PS, plus de 1 200 PS ou 1 230 PS. Le modèle doit donc séparer au moins
  le réglage de course 1973 et le réglage record avec échangeurs de 1975.
- Les 24 l d'huile publiés pour le moteur et le réservoir de 55 l décrit sur une
  917 KH ne sont pas deux mesures interchangeables.
- La désignation KKK rencontrée dans des sources ultérieures ne doit pas être
  appliquée au 917/30 historique sans preuve. Les sources allemandes retenues
  pointent vers Eberspächer, mais ne donnent ni référence ni carte turbo.
- Les soupapes d'échappement en titane ne sont pas établies par une source
  primaire allemande. Les bielles en titane sont mieux documentées, mais leur
  nuance et leur traitement restent inconnus.
- Un moteur conceptuel de 1 600 ch doit rester une variante non historique,
  séparée du 917/30 documenté.

## Données encore absentes

Les sources publiques consultées ne fournissent pas :

- l'enveloppe cotée du moteur et les plans de joints ;
- la longueur du vilebrequin, les diamètres des tourillons/manetons et leurs
  déports ;
- l'entraxe des bielles, les dimensions des axes et les détails de boulonnerie ;
- le motif complet de fixation des culasses, au-delà du nombre et de la cote
  extérieure des goujons ;
- les chambres, conduits, ailettes et épaisseurs de paroi ;
- les alliages exacts, états métallurgiques et traitements thermiques ;
- la référence et les cartes compresseur/turbine Eberspächer ;
- les diamètres de galeries, jeux, débits et courbes des pompes ;
- une nomenclature Porsche complète avec références de pièces.

Ces champs doivent rester `unknown` ou `provisional`. Ils ne peuvent être
complétés qu'avec des dessins Porsche autorisés, une métrologie/CT calibrée d'un
moteur accessible légalement ou une collaboration documentée avec un motoriste.
Le [Porsche Archiv](https://pnr-prd2-pub2.newsroom.porsche.com/de/pressemappen/Porsche-Museum/Archiv-und-Sammlung.html)
est la voie licite à privilégier pour les dessins historiques.

## Réutilisation

Les [conditions du Porsche Newsroom](https://newsroom.porsche.com/de/bilder-videos/porsche-newsroom-nutzungshinweise.html)
réservent les textes, images, vidéos et autres médias à des usages encadrés. Les
autres éditeurs consultés n'affichent pas de licence ouverte pour leur contenu.
Le dépôt conserve donc uniquement des fiches de provenance et des faits
paraphrasés ; aucun média, plan ou modèle provenant de ces pages ne doit être
redistribué.
