# Phase 1 — Inventaire des sources

Ce document suit l’avancement de la Phase 1. Il n’héberge aucun contenu protégé :
il enregistre où une information se trouve, comment elle a été consultée et ce
que son statut juridique autorise.

## Lot 1 — Catalogues officiels, manuels légalement accessibles et mesures

Consulté le 28 août 2026. Chaque URL a été ouverte avant d’être inscrite ; les
échecs d’accès sont conservés au même titre que les succès.

### Catalogues et documents officiels

| Fiche | Contenu | Accès | Réutilisation | Preuve |
|---|---|---|---|---|
| `SRC-PORSCHE-PET-993` | Catalogue Pièces d’Origine Porsche Classic | disponible | interdite | A |
| `SRC-PORSCHE-NEWSROOM-993` | Dossier historique et gamme | disponible | interdite | A |
| `SRC-PORSCHE-NEWSROOM-993-30Y` | Dossier de presse « 30 ans du 993 » | disponible | interdite | A |
| `SRC-PORSCHE-SHOP-TECHLIT` | Littérature technique officielle à l’achat | disponible, catalogue vide | interdite | non noté |
| `SRC-PORSCHE-CLASSICSHOP-USA` | Ancienne boutique Classic (manuels 993) | hors service (DNS) | interdite | non noté |

### Manuels et données techniques accessibles

| Fiche | Contenu | Accès | Réutilisation | Preuve |
|---|---|---|---|---|
| `SRC-9XXTEILE-PET-DIAGRAMS` | Vues éclatées et numéros de pièces | libre | interdite | C |
| `SRC-PCA-993-ALIGNMENT` | Réglages de trains d’origine | libre | interdite | C |
| `SRC-WIKIPEDIA-993` | Encombrement véhicule et variantes | libre | attribution requise | D |
| `SRC-STUTTCARS-993-PARTS` | Diagrammes PET annoncés | payant | inconnue | non noté |
| `SRC-STUTTCARS-993-TORQUE` | Couples de serrage moteur | payant | inconnue | non noté |
| `SRC-PORSCHEFANATICS-993-MANUAL-DATA` | Index public et données dérivées du manuel : 235 procédures, 195 couples et 111 valeurs techniques | disponible | référence seulement | C |

### Mesures et données dimensionnelles

| Fiche | Contenu | Accès | Réutilisation | Preuve |
|---|---|---|---|---|
| `SRC-CARGEOMETRY-993-BODY` | Points de mesure caisse et soubassement | achat (20 USD) | interdite | B |
| `SRC-WHEEL-SIZE-993` | Jantes, déports, entraxe | libre | inconnue | C |
| `SRC-CARFOLIO-993` | Masses et cotes par variante | libre | interdite | D |
| `SRC-ELFERCLASSIC-993-TECHNICAL-DATA` | Compilation allemande : encombrement du 993 Carrera 2 ROW (4245 × 1735 × 1300 mm), empattement, voies, garde au sol et références de géométrie | accès expiré | non redistribuable | C |
| `SRC-RENNLIST-993-FORUMS` | Mesures d’atelier communautaires | bloqué aux robots | inconnue | C |
| `SRC-PELICANPARTS-964-993-FORUM` | Mesures d’atelier communautaires | bloqué aux robots | inconnue | C |

## Sources écartées

Écartées sans être inscrites au registre. Le motif est conservé pour éviter de
les réexaminer.

| Source | Motif |
|---|---|
| Scribd, SlideShare, eManualOnline, eManuals, workshopcarmanuals | Rediffusion du manuel d’atelier Porsche sans droit démontrable |
| Miroir GitHub du livret `Technical Specifications 911 Carrera (993)` | La copie publique permet de lire la table d'usine « Dimensions for Floor System » (page 110), mais l'hébergement et les droits de reproduction ne sont pas établis; aucun PDF n'est conservé |
| Pièces jointes de forum contenant des planches cotées d’usine | Même document protégé, republié par un tiers |
| Agrégateurs de PDF sans éditeur identifiable | Provenance invérifiable |

Une source écartée peut rester utile comme indice de l’existence d’un document.
Elle ne devient jamais une référence du catalogue.

## Constats du lot 1

- Aucun plan coté d’usine n’est légalement accessible librement. Les vues
  éclatées renseignent l’assemblage et la nomenclature, pas la géométrie.
- La donnée dimensionnelle exploitable viendra de la mesure directe, complétée
  par un référentiel de caisse acheté (`SRC-CARGEOMETRY-993-BODY`).
- Les numéros de pièces sont accessibles gratuitement, mais leur rediffusion ne
  l’est pas : ils servent d’identifiant de travail, pas de contenu publié.
- Deux forums majeurs refusent l’accès automatisé ; leur consultation reste
  manuelle et chaque valeur reprise doit être remesurée.
- Le corpus communautaire recopie fréquemment la même origine non citée ; la
  règle « deux copies ne font pas deux confirmations » s’applique directement.
- Le miroir public du livret technique Porsche `1st Edition, Status 8 1995`
  confirme l'existence d'une table de contrôle du plancher : A/P21 440 ± 2 mm,
  B/P3 670 ± 0,5 mm, C/P5 770 ± 2 mm, D/P6 204 ± 2 mm, E/P18 1330 ± 1 mm,
  F/P19 1236 ± 1 mm, G/P12 278 ± 1 mm, H/P20 1018 ± 1 mm, I/P13 935 ± 1,5 mm,
  K/P14 973 ± 1,5 mm et L/P22 640 ± 1 mm. Le document précise que les cotes
  partent du centre des trous ou points de vis et que les cotes entre parenthèses
  sont horizontales. Ces valeurs sont une piste pour acheter ou consulter un
  exemplaire autorisé, pas des mesures du projet ni une géométrie redistribuable.

## Lot 2 — Modèles 3D et jumeaux numériques

Recherché en anglais et en allemand le 28 août 2026, sur les places de marché
3D, les boutiques de scans, les services de numérisation et la presse
technique.

### Le constat

**Aucun jumeau numérique du 993 librement réutilisable et vérifié n'a été
trouvé.** Des scans commerciaux de carrosserie existent, mais ils sont
extérieurs, soumis à achat, déclaratifs et sans rapport de métrologie public.
Ce qui existe se range en quatre catégories :

| Catégorie | Exemple | Niveau | Ce que ça vaut |
|---|---|---|---|
| Maillage visuel de synthèse | modèles de jeu, banques 3D, RWB Sketchfab | D | Silhouette, jamais une interface |
| Scan brut sans échelle | `SRC-SKETCHFAB-993-GT2-RAW-SCAN` | E | Forme, pas mesure |
| Scan commercial de composant | `SRC-BREMAR-3D-SCAN-STORE` | D | Aucun composant 993 |
| Scan commercial de carrosserie | `SRC-WOLFE-993-TURBO-EXTERIOR-SCAN`, `SRC-SKETCHFAB-993-BARN-FIND-SCAN` | D | Extérieur déclaré à 1,76–2 mm, sans cotes vérifiées ni licence de redistribution |

Le seul scan complet de carrosserie 993 rencontré avec une licence libre
déclarée reste le scan brut du GT2, en CC BY 4.0. Il a été obtenu par
vidéogrammétrie sur 115 images tirées d'une vidéo YouTube : ni échelle, ni
précision annoncée, et une chaîne de droits qui n'est pas étanche puisqu'il
dérive d'images appartenant à un tiers. En revanche, l'archive
`SRC-RENN3DPARTS-993-OPEN-FILES` recense neuf fichiers de pièces sous licences
déclarées par fiche (CC-BY, CC-BY-SA, CC-BY-NC, CC-BY-NC-SA ou domaine public).
Ces meshes de pièces ne sont ni un scan de véhicule ni une preuve de précision
d'interface; la licence primaire et les unités doivent être confirmées avant
redistribution. La
[recherche germanophone complémentaire](research/phase-1-recherche-allemande.md)
a recensé d'autres assets communautaires à licence déclarée, à confirmer sur
leurs publications originales. Aucun de ces assets n'est dimensionnellement
qualifié. Les deux scans de carrosserie commerciaux restent donc des pistes
d'achat et de comparaison, pas des substituts libres.

### Ce qui existe, mais hors de portée

Porsche Classic fait déjà exactement ce travail, en interne
(`SRC-PORSCHE-CLASSIC-3D-PRINTING`) : SLM pour l'acier, SLS pour les polymères,
et « un scan 3D du composant suffit comme base pour lancer la production ». Huit
pièces produites, une vingtaine à l'étude, contrôlées par essai de pression,
tomographie et vérification de montage sur véhicule.

C'est à la fois une validation de la démarche et la barre à franchir. Le
constructeur ne publie pas ces données.

### La piste qui aurait passé à l'échelle, et qui est fermée

`SRC-CAR-CLOUDS-POINT-CLOUDS` vend des nuages de points laser de véhicules
entiers à 195 USD. Un scan de voiture complète donnerait l'environnement de
montage de dizaines de pièces d'un coup, là où une mesure de pièce n'en sert
qu'une : c'était la meilleure réponse au problème d'échelle.

Catalogue interrogé en entier le 28 août 2026 — 906 produits, cinq Porsche :

| Modèle | Prix |
|---|---|
| Porsche 911 Cabriolet (996) 2001 | 195 USD |
| Porsche 911 2015 (991) | 195 USD |
| Porsche Cayenne 2019 et 2020 | 195 USD |
| Porsche Macan 2019 | 195 USD |

**Aucun 993, et aucun refroidi par air.** Le plus proche est un 996 : génération
suivante, caisse entièrement différente. Ce n'est pas un substitut.

Le livrable est un nuage de points E57, intérieur inclus. La piste ne se
rouvrirait que par une commande de numérisation dédiée, d'un tout autre ordre de
prix — ou par un autre prestataire, restant à identifier.

## Lot 5 — Recherche allemande, mesures et scans 993

Consulté les 29 et 30 août 2026. Les résultats sont enregistrés dans le registre des
sources; aucune image de forum, pièce jointe protégée, numérisation brute ou
fichier CAO tiers n'est copié dans le dépôt.

### Mesures communautaires

| Fiche | Résultat | Niveau | Décision |
|---|---|---|---|
| `SRC-PFF-993-RS-LETTERING-MEASUREMENT` | Monogramme Carrera RS : 28,5 cm de chaque côté, 6 cm depuis le bord inférieur, 33 cm de longueur, 3 cm de hauteur | C | Piste à remesurer, aucune géométrie publiée |
| `SRC-PFF-993-CABRIO-ROOF-BUSHING-MEASUREMENT` | Bague de capote : Ø extérieur 12 mm, Ø intérieur 10 mm, profondeur 9 mm, avec collerette | C | Piste à remesurer sur pièce déposée; aucune déclaration d'interchangeabilité |
| `SRC-PFF-993-SPEAKER-DIAMETERS` | Haut-parleurs annoncés à 165 mm à l'avant et 130 mm à l'arrière sur un Cabrio de 1997; profondeur inconnue | C | Contexte de support audio; mesurer aussi profondeur, ouverture et fixations |
| `SRC-PFF-993-FRONT-SPEAKER-MEASUREMENT` | Un autre fil allemand indique 13 cm à l'avant hors Sound-Paket et une modification importante pour passer à 16 cm | C | Contradiction avec les 165 mm rapportés sur un Cabrio; distinguer variante audio, diamètre nominal et ouverture par mesure directe |
| `SRC-PFF-993-SUNROOF-REVERSE-ENGINEERING` | Reconstruction de pièces de toit ouvrant 993 en polymère renforcé | non noté | Projet intéressant à contacter; ni cote ni CAO publiée |
| `SRC-PFF-993-RS-SPRING-DATA` | Diamètres de fil et raideurs de ressorts RS rapportés par le forum | C | Documenté, mais exclu des décisions de fabrication : suspension critique |
| `SRC-PFF-993-STABILIZER-BAR-DIAMETER` | Diamètre arrière déclaré à 18 mm sur un C2 Tiptronic 1995, dans une plage de 18–21 mm | C | Mesure directe obligatoire; suspension critique, aucune fabrication |
| `SRC-PFF-993-DISTRIBUTOR-BEARING-DIMENSIONS` | Roulements de distributeur 964/993 déclarés à environ Ø32 mm extérieur, Ø12,45 mm intérieur et 10 mm de hauteur | C | Mesure communautaire sans instrument, répétitions, variante ni datum; identifier et mesurer la pièce déposée avant tout remplacement |
| `SRC-PFF-993-BRAKE-LIGHT-SWITCH-TRAVEL` | Course déclarée du contacteur de feu stop : 6–16 mm, mesurée au milieu du caoutchouc de pédale sur une 993 Tiptronic | C | Réglage de sécurité sans instrument, répétitions ni année; vérifier dans la documentation d'atelier et sur le véhicule, aucune fabrication ou modification |
| `SRC-ELFERSZENE-993-VALVE-SPRING-INSTALLATION-LENGTH` | Procédure allemande et longueurs montées déclarées pour ressorts de soupapes 993 : admission 36,7 + 0,3 mm / échappement 35,7 + 0,3 mm, ou 37,2 + 0,3 mm / 35,8 + 0,3 mm pour M64/20 RS | C | Page bloquée, valeurs issues de l'index sans validation indépendante; distribution fortement chargée, aucune reproduction ou libération sans revue d'ingénierie et validation fatigue |

Ces valeurs sont des déclarations de membres, sans instrument, répétition,
référentiel de mesure ou validation indépendante. Elles servent à préparer une
mesure directe et non à marquer une pièce « précise », « ajustée » ou « testée ».

### Prestataires et fabricants allemands

| Fiche | Ce qui est démontré | Ce qui manque |
|---|---|---|
| `SRC-DENK3D-993-SWITCH-PANEL-REPAIR` | Kit PETG CF imprimé pour pattes cassées de platines 964/993; références 96455207104 et 96455213501 | Pas de scan, de CAO, de cotes ni de licence; la platine complète n'est pas vendue |
| `SRC-BESPOKE-ELEMENTAL-993-CARBON-SWITCH-PANELS` | Fabricant affichant des Schalterblenden carbone 993/964; variante recouverte à partir de la pièce d'origine et variante autoclave moulée | B déclaré | Aucun plan, scan, cote, tolérance ou rapport; demander un échantillon et distinguer la version recouverte de la pièce de remplacement |
| `SRC-PARTWORKS-993-INTERIOR-REPRODUCTIONS` | Catalogue 993 : clips de pare-soleil (18/25 mm), deux lampes Hella (133 × 30 mm, 89 × 33 × 28 mm) et afficheur de compteur 964/993 (27 × 62 mm) | Cotes produit déclarées, sans protocole de mesure ni fichier réutilisable; vérifier la variante et l'interface sur échantillon |
| `SRC-FEBOE-964-993-ALTERNATOR-BELT-DIMENSIONS` | Fiche allemande FEBÖ : courroie 964/993 réf. Porsche 999 192 338 50 annoncée en 10 × 775 mm, pour alternateur/ventilateur | Déclaration de produit sans profil, tolérances, longueur de référence, poulies ou mesure indépendante; donnée d'entretien uniquement, aucune reconstruction ou libération sans vérification |
| `SRC-TECHSCAN3D-GERMANY-LIDAR-CAD-SERVICE` | Prestataire allemand annonçant le scan de véhicules anciens, les nuages LiDAR PTX/BTX/XYZ et E57, les mesures CSV/DXF/XML et la CAO STEP/IGES | Aucun projet 993, fichier public, rapport d'incertitude ou licence de réutilisation; demander un scan sous contrat avec datums, échelle, données brutes et droits explicites |
| `SRC-PARTWORKS-993-VALVE-STEM-SEAL-DIMENSIONS` | Fiche allemande partworks/Elring : joint de queue de soupape 993 annoncé à 10,4 mm de haut, Ø14,2 mm extérieur, Ø10,8 mm intérieur et queue 8 mm | Cotes produit sans profil, tolérances, matériau, preuve d'équivalence OEM ou mesure indépendante; étanchéité moteur, aucune reproduction ou libération sans caractérisation et validation |
| `SRC-FVD-993-LOWER-CONSOLE-COVER-DIMENSIONS` | Fiche allemande FVD : cache inférieure de console 993 réf. 99363207110 annoncée 110 × 80 × 40 mm, 0,06 kg, sans lampes et avec deux clips par cache | C | Contradiction entre le titre (Coupé sans M425/M650) et la table de compatibilité; encombrement commercial sans datums, découpes, clips, tolérances, CAO ou mesure indépendante |
| `SRC-CLASSICPARTS-993-AIR-FUNNEL-DIMENSIONS` | Fiche allemande Classic Parts : jeu de six cornets d'admission compatible 993 3,6–3,8 annoncé à 40 × 34 mm et 0,9 kg, réf. AT83144 / PM-O180-3 | C | Dimensions commerciales sans dessin, cotes de montage, tolérances, protocole ou distinction claire entre pièce unitaire et ensemble; fabricant indiqué JP Group A/S, échantillon à mesurer avant toute reproduction |
| `SRC-FVD-993-HOT-AIR-CONNECTING-PIECE-DIMENSIONS` | Fiche allemande FVD : raccord d'air chaud 993 réf. 99321134601, annoncé à 0,18 kg pour les carrosseries Cabrio, Coupé et Targa | C | Poids commercial sans diamètres, épaisseurs, rayons, tolérances ou protocole; commander un échantillon et recouper avec la piste d'atelier Rennlist |
| `SRC-FVD-993-BITURBO-REAR-SPOILER-DIMENSIONS` | Fiche allemande FVD : spoiler arrière Bi-Turbo GFK 993 annoncé à 145 × 63 × 27 cm et 6,7 kg | C | Enveloppe aftermarket sans perçages, datums, tolérances ni validation aérodynamique; benchmark uniquement, aucune reproduction ou modification sans contrôle de variante et validation |
| `SRC-DESIGN911-993-INSTRUMENT-80MM` | Bouchon d'horloge listé pour 993 1994–1998, prévu pour un instrument de 80 mm de diamètre | Diamètre nominal de l'instrument, pas découpe ou interface OEM; plan, tolérance et mesure indépendante absents |
| `SRC-PARTWORKS-993-ODOMETER-GEAR` | Pignon E15 annoncé à Ø 6,90 mm et 15 dents, avec variante de pignon conjugué 17-K et distinction EU/US | Donnée produit issue d'un fabricant, sans protocole, dessin ou CAO; fabrication annoncée par injection, pas impression 3D |
| `SRC-WOLFCARHIFI-993-SCAN-CAD-ADAPTERS` | Produits 993 annoncés issus de scan/CAO/impression, adaptateurs 130, 4×6 et 165 mm | Interfaces complètes, fichiers et rapport d'essai non publiés |
| `SRC-WOLFCARHIFI-993-REAR-100MM-SCAN` | Adaptateur arrière annoncé pour haut-parleur 100 mm, conçu à partir de scans 3D de la plage arrière 993 et imprimé en plastique haute température | Fichier, plan, coordonnées et rapport non publiés; 100 mm concerne le haut-parleur, pas l'interface Porsche |
| `SRC-KLASSIKERAUTORADIO-993-REAR-SPEAKER-DIMENSIONS` | Fabricant allemand : haut-parleur arrière de remplacement 993 annoncé 90 × 150 mm, profondeur 50 mm et aimant Ø80 mm | Cotes du produit de remplacement, pas ouverture OEM ou entraxes; aucune CAO, tolérance ou mesure indépendante; acheter un échantillon |
| `SRC-SONORITY-993-M490-SPEAKER-DIMENSIONS` | Fournisseur allemand : système compatible M490 avec woofer 130/116,5/58,5 mm, medium 90/73/37 mm et tweeter, découpe 48 mm/profondeur 22 mm | Cotes des haut-parleurs, pas des supports Porsche; aucune interface, mesure indépendante ou tolérance; utile pour cadrer une campagne audio |
| `SRC-AIRAX-993-WIND-DEFLECTOR-DIMENSIONS` | Documentation allemande AIRAX : coupe-vent 964/993, encombrement 33 × 33 × 97, masse 3,00 kg et matériaux du cadre, de la housse et de la maille | Dimensions hors-tout sans points d'ancrage, tolérance, coupe ou CAO; fixation et visibilité à vérifier sur cabriolet |
| `SRC-WS-AUTOTEILE-993-FRONT-PLATE-HOLDER-DIMENSIONS` | Fiche allemande du support de plaque avant 993 701 105 00 : largeur 439 mm, hauteur 80 mm, incompatibilité annoncée avec la plaque UE standard | Aucun entraxe, trou, épaisseur, rayon, datum ou contrôle indépendant; acheter un exemplaire avant tout gabarit |
| `SRC-FSH-993-INSTRUMENT-RINGS` | Fabricant allemand : jeu de cinq bagues en aluminium pour instruments 911/964/993, montage par clips et masse annoncée d'environ 0,06 kg | Aucun diamètre, largeur, épaisseur, profondeur, tolérance ou CAO; acheter un échantillon avant reconstruction |
| `SRC-TECHART-993-INSTRUMENT-RINGS-MANUAL` | Notice allemande TECHART pour les bagues 964/993 : référence 093.460.106.009, nettoyage, 5–6 points de collage et bande adhésive de 3 mm maximum | Notice de montage sans cotes ni CAO; utile pour préparer la dépose et repérer la zone de contact, pas pour valider une reproduction |
| `SRC-CULTS-993-WHEEL-CENTER-CAP-CAD` | Modèle commercial allemand proposant quatre fichiers STEP/STL pour un cache-moyeu associe à la référence 993 361 303 11 | Dimensions, mesure, scan et licence non vérifiés; pièce de roue à soumettre à mesure et revue d'ingénierie |
| `SRC-PARTWORKS-993-C4-CENTER-TUBE-MEASUREMENT` | Fabricant allemand : remise en état du tube central 993 C4 avec contrôle de rectitude, positionnement des roulements et contrôle des surfaces fonctionnelles | Aucun résultat chiffré, tolérance, rapport ou CAO; organe de transmission fortement chargé, piste de contact uniquement |
| `SRC-ELEVEN-993-DOOR-WINDOW-FRAME-MOUNTING-PLATE` | Vendeur allemand : petite plaque de fixation du cadre de vitre annoncée comme pièce Porsche d'origine, repère 10 de diagramme, compatibilité 993 Coupé 1995–1998 | Aucune référence Porsche, cote, épaisseur, perçage, tolérance ou mesure indépendante; acheter et identifier la pièce avant toute reconstruction |
| `SRC-TECHART-993-FENDER-AIR-DUCT-MANUAL` | Notice allemande TECHART : gabarit de découpe d'aile, avant-trous de Ø2,5 mm, découpe, soudure TIG et traitement anticorrosion pour conduit d'air 993 | Gabarit, coordonnées, rayons, tolérances et CAO absents; modification de carrosserie aftermarket, à contrôler avant toute reproduction |
| `SRC-ELEVEN-ENGINEERING-OLDTIMER-RE` | Flux professionnel scan → reconstruction CAO paramétrique; droits contractuels explicités | Aucun cas 993 public; tolérance de ±0,1 mm déclarée, non auditée ici |
| `SRC-ZESAD-993-TURBO-SCAN-TO-CAD` | Service scan et reconstruction STL vers STEP pour une application 993 Turbo | Aucun fichier public; volant moteur = pièce chargée, hors catalogue sans ingénierie |
| `SRC-GOTECH-CLASSIC-PARTS-RE` | Prestataire de Weissach : scan laser de pièces et de leur situation de montage, préparation des données 3D pour fabrication | Aucun cas 993 public, rapport de métrologie, tolérance ou licence de CAO; à solliciter pour une petite pièce intérieure non critique |

| `SRC-OPTI3D-GERMANY-SCAN-CAD-RE` | Prestataire allemand de Troisdorf : scanners Zeiss/Artec/Scantech, scan mobile, nuage de points vers modèle volumique CAO et reproduction de pièces anciennes | Aucun cas 993 public, rapport, incertitude ou licence de livrable; demander une campagne contractuelle sur une pièce non critique |
| `SRC-FORMAG-GERMANY-MOBILE-LASER-SCAN` | Prestataire allemand : scanner laser mobile, précision annoncée jusqu'à 0,1 mm, maillage et scan-to-CAD, intervention possible en Allemagne | Aucun cas 993 public; performances commerciales à confirmer par rapport, datums, surfaces masquées et droits; tarif indicatif 1 190 EUR HT pour environ 7 h |
| `SRC-Q-TECH-RODING-CT-SCAN-CAD` | Prestataire allemand : CT ZEISS jusqu'à Ø275 × 360 mm ou Ø615 × 870 mm, conversion CT/scan vers STEP et extraction de zones intérieures/extérieures | Aucun cas 993 public; paramètres et accréditation déclarés par le prestataire, à confirmer par rapport, datums, incertitude et contrat de droits |
| `SRC-MOUMAMOTION-GERMANY-3D-SCAN-CAD-SERVICE` | Prestataire allemand d'Offenbach : scan sans contact annoncé à 0,05 mm, reconstruction CAO avec tolérances et fabrication FDM/SLA de pièces d'oldtimer; pièce originale acceptée par envoi | Aucun cas 993, CT ou LiDAR public; précision déclarée sans rapport ni répétition; demander datums, surfaces cachées, format éditable et droits |
| `SRC-PFF-993-CDR21-LOGO-MEASUREMENT` | Deux membres d'un forum allemand mesurent le logo Porsche d'une radio Becker CDR-21/2238 à 33 mm et 32,5 mm, avec une photographie | C | Mesure communautaire sans instrument, variante de logo, tolérance ou véhicule 993 établis; référence pour mesure directe d'une radio déposée, pas interface de console |
| `SRC-PFF-993-CABRIO-LOCKING-MOTOR-MEASUREMENT-LEAD` | Schéma allemand demandant les cotes A/B du moteur de verrouillage de capote d'une 993 Cabriolet 1996 | D | Aucune réponse chiffrée, tolérance ou protocole; piste de contact seulement, mécanisme de retenue à soumettre à validation mécanique |
| `SRC-MAKO-GERMANY-POINTCLOUD-NATIVE-CAD` | Prestataire allemand de Straelen : conversion de nuages de points ou scans en CAO native, historique de construction et contrôle nuage/CAO annoncés | Aucun cas 993, rapport ou fichier public; échantillon derrière formulaire et précision de 0,05 mm annoncée pour l'équipement, pas pour une pièce 993 |
| `SRC-KLEINANZEIGEN-993-CABRIO-REAR-SPEAKER-MEASUREMENT` | Annonce allemande d'un kit de haut-parleurs arrière pour 993 Cabriolet : panier 100 mm, profondeur d'installation environ 46 mm et entraxe diagonal environ 115 mm | C | Cotes approximatives d'un remplacement non original, sans datum, instrument, tolérance ou interface OEM; comparer sur un échantillon avant toute adaptation |
| `SRC-PFF-993-HEADLAMP-REFLECTOR-RIVET-HOLES` | Fil allemand : trous du réflecteur de phare annoncés à environ 3 mm, avec remontage possible par vis M3 de 5 mm | C | Cote communautaire sans plan, instrument ou tolérance; variante de phare et alignement optique à vérifier sur pièce déposée |

### Scans de carrosserie et preuve constructeur

| Fiche | Accès et portée | Niveau |
|---|---|---|
| `SRC-SHINING3D-993-SCAN-CASE` | Étude allemande documentant le scan réel d'une 993 de 1995 avec 8,6 m de tracking et 206,7 m³ de volume de mesure; aucune donnée livrée. Les 0,02 mm sont une caractéristique annoncée de l'équipement, pas le résultat du scan 993 | B déclaré |
| `SRC-WOLFE-993-TURBO-EXTERIOR-SCAN` | OBJ commercial d'une 993 Turbo extérieure, précision annoncée 1,76 mm; ligne de toit signalée moins bonne | D déclaré |
| `SRC-SKETCHFAB-993-BARN-FIND-SCAN` | Scan commercial extérieur Carrera annoncé à 2 mm; achat et conditions de licence à vérifier | D déclaré |
| `SRC-PORSCHE-CT-WEISSACH` | Porsche documente sa capacité de tomographie CT, mais ne publie aucun scan 993 ni jeu de données exploitable | A, sans donnée 993 |

**Conclusion du lot 5 :** aucune donnée CT, LiDAR ou scan laser 993 librement
téléchargeable avec droits et précision vérifiés n'a été trouvée. La meilleure
prochaine acquisition est une mesure directe d'une petite pièce non critique,
avec variante, instrument, répétitions, photos de référence et autorisation de
réutilisation documentée. Les scans de carrosserie commerciaux peuvent aider à
la silhouette ou à préparer une campagne de mesure, mais ne doivent pas fournir
à eux seuls les interfaces de fabrication.

## Lot 6 — Deuxième passage : forums, places de marché et prestataires de scan

Recherche complémentaire les 29 et 30 août 2026, avec des requêtes allemandes et des
fils d'amateurs consacrés à la conception, à l'impression et à l'ajustement de
pièces de 993. Les pages Rennlist n'ont pas pu être relues automatiquement; les
résultats indexés sont conservés comme pistes et non comme fichiers réutilisables.

### CAO et ajustement communautaires

| Fiche | Résultat | Niveau | Décision |
|---|---|---|---|
| `SRC-RENNLIST-993-REAR-SPEAKER-MOUNTS` | Support Fusion 360 imprimé sur CR-10 pour haut-parleurs arrière; grille OEM conservée; ajustement PLA rapporté « quite good » sur un Pioneer | C | Demander le STL et les droits à l'auteur; vérifier chaque haut-parleur sur pièce déposée |
| `SRC-RENNLIST-993-REAR-SPEAKER-FRAMES-STEP` | Fichiers STEP Fusion 360 transmis entre amateurs, puis cadres affinés par mesures et impression pour des haut-parleurs Infiniti Kappa avec grilles OEM | C | Fichier, protocole, variantes audio et licence non publics; contacter l'auteur et remesurer l'interface |
| `SRC-RENNLIST-993-HIFI-SPEAKER-ADAPTER-DIMENSIONS` | Platine d'adaptation de porte cotée à environ 18 × 9¼ pouces, avec positions de perçage et découpes; haut-parleur arrière 4 × 6 ajusté sous grille OEM | C | Cotes d'un montage personnel, pas de la pièce OEM; pas d'instrument, CAO ou licence; remesurer selon la variante audio |
| `SRC-GRABCAD-964-993-TWEETER-GRILL-BRACKET` | Support CAO pour revisser une grille de tweeter de porte 964/993, référence OEM 91155567300 mentionnée; clips du tweeter d'origine exclus | D | Page GrabCAD bloquée; fichier, cotes, format editable et licence à obtenir auprès de l'auteur avant tout usage |
| `SRC-THINGIVERSE-993-REAR-SPEAKER-SHIM` | STL indexé comme cale de haut-parleur arrière 993 sur laquelle la grille d'origine se clipse | D | Source primaire et licence non vérifiées; aucune cote ni mesure indépendante; récupérer légalement et comparer sur pièce |
| `SRC-CULTS-964-993-CONSOLE-REPAIR-STL` | Deux STL gratuits pour réparation de console 964/993, avec bboxes de fichier publiées et auteur identifié | D | Champ de licence vide; téléchargement et redistribution à suspendre, bboxes non assimilables à des cotes d'interface |
| `SRC-CULTS-993-DOOR-POCKET-REINFORCEMENT` | Renfort de vide-poches de porte 993 non-Hifi : deux STL et bboxes annoncées 75,184 × 12,7 × 73,660 mm | D | Fiche Cults bloquée à l'accès direct; licence, fichier et ajustement à confirmer, bbox non assimilable à une cote OEM |
| `SRC-RENNLIST-993-SEAT-RAIL-BUSHING-CAD` | Fil de propriétaires signalant une pièce de remplacement de glissière et une archive `993 seat rail bushing v3.zip` | C | Téléchargement et licence non vérifiés; glissière de siège liée à la retenue et au positionnement de l'occupant, aucune libération sans revue d'ingénierie |
| `SRC-RENNLIST-993-DOOR-POCKET-REINFORCEMENT` | Empreinte au mastic et plusieurs impressions d'essai pour un renfort de vide-poche; écarts d'ajustement et déformations documentés | C | Très bonne piste de méthode et de test-fit, mais aucune cote ou CAO réutilisable récupérée |
| `SRC-RENNLIST-993-DOOR-POCKET-DIMENSION-LEAD` | Cotes partielles déclarées d'environ 50 mm (standard) et 35 mm (HiFi), avec mention d'un dessin CAO de renfort | C | Valeurs de discussion non instrumentées; cote critique du modèle standard, fichier et droits à obtenir puis remesurer |
| `SRC-RENNLIST-993-SWITCH-REPAIR-CAD` | Tentative de reconstruction d'un composant plastique de switch; quatre cotes de pion proposées pour une modélisation SolidWorks | C | Le projet semble abandonné; aucune cote finale ni CAO accessible |
| `SRC-RENNLIST-993-HVAC-BUTTONS-CAD` | Boutons de remplacement du bloc de climatisation conçus par un amateur pour 964, compatibilité 993 annoncée, impression via Shapeways | C | Fichier, cotes, essai 993 et licence non vérifiés; contacter l'auteur avant toute réutilisation |
| `SRC-PFF-993-REAR-SPOILER-HOLE-SPACING` | Mesure communautaire d'environ 79 mm sur la charnière et 62 mm sur le spoiler lors d'un montage Turbo | C | Variante et repères non établis; zone soumise aux efforts aérodynamiques, aucune fabrication ni perçage sans vérification et revue |
| `SRC-SHAPEWAYS-993-SUN-VISOR-GOPRO-CLIP` | Article Shapeways : clip droit de pare-soleil 993 imprimé en 3D, support GoPro intégré et montage direct annoncé; ajustement volontairement serré | B déclaré | Fichier, cotes, matériau, auteur et licence non vérifiés; retrouver l'échantillon avant toute réutilisation |
| `SRC-RENNLIST-993-SPLIT-GRILL-CAD` | Gabarits papier, prototypes imprimés et mesure de courbure du capot moteur; modèle final séparé vers 360 mm, coque 2,4 mm | C | Bon protocole de développement, mais fichier et droits absents; confirmer le matériau et l'ajustement |
| `SRC-RENNLIST-993-DOOR-SPEAKER-POD` | Pod de porte 993 Targa avec Ø intérieur 73–74 mm, cercle d'inserts Ø 80 mm et grand logement d'environ 6,5 pouces | C | Valeurs issues d'un montage Focal K2; remesurer selon le haut-parleur et obtenir le fichier |
| `SRC-RENNLIST-993-WINDSHIELD-TEMPLATES` | Trois gabarits imprimables pour la profondeur de pose des vitrages; fichiers 3D reliés par l'auteur, environ 5 mm d'épaisseur et plateau minimal 7 × 3 pouces | C | Reconstruction depuis tracés, contrôle annoncé à moins de 1 mm, mais page, fichiers et licence non vérifiés; différence de vitrage RS à confirmer |
| `SRC-RENNLIST-993-BUMPERETTE-DELETE-CAD` | Inserts de suppression de bumperettes modélisés, testés puis proposés via Shapeways en plusieurs matériaux | C | Le fichier et ses droits ne sont pas publics; le lien marketplace est incomplet |
| `SRC-THANGS-993-UPPER-CONSOLE-TABS` | STL commercial annoncé à 68 × 6 × 29 mm pour les pattes supérieures de console 964/993 | D | Achat et licence à vérifier; la bbox et « perfect fit » sont des déclarations du vendeur |
| `SRC-THANGS-993-LOWER-CONSOLE-TABS` | STL commercial annoncé à 87 × 12 × 31 mm pour les pattes inférieures de console 964/993 | D | Piste voisine du panneau de commande, pas preuve de géométrie du switch blank |
| `SRC-CULTS-993-DOOR-SCAN` | STL commercial d'une porte G-body avec adaptation de poignée 993 et cadre Targa, dimensions de fichier annoncées | D | Panneau modifié, pas porte OEM; achat, licence et comparaison à l'original obligatoires |
| `SRC-CGTRADER-993-DASHBOARD-SCALE-MODEL` | Modèle de tableau de bord annoncé en STL/OBJ/DXF/FBX/glTF, mais explicitement dessiné pour un modèle réduit 1/8 et imparfait | E | Faux positif CAD; unités millimétriques affichées mais échelle et exactitude incompatibles avec une géométrie de fabrication 993 |
| `SRC-RENN3DPARTS-993-OPEN-FILES` | Archive communautaire de neuf fiches 993 avec STL, photos, bboxes et licences par fiche : CC-BY, CC-BY-NC, CC-BY-SA, CC-BY-NC-SA ou domaine public selon l'auteur | D | Les fichiers restent des meshes sans mesure indépendante; confirmer la source primaire, les unités et les droits avant redistribution; aucun fichier copié dans le dépôt |
| `SRC-THINGIVERSE-993-POLLEN-TABS` | Modèle primaire Thingiverse `thing:2152823` de LimeyBoy, avec variantes de remplacement et de renfort des pattes de filtre à pollen | C | Page moderne, fichiers et licence non lisibles automatiquement; bbox secondaire d'environ 30,700 × 18 × 10,800 mm à vérifier |
| `SRC-PELICAN-993-FAN-SHROUD-DELETE-CAD-LEAD` | Demande d'un utilisateur basé en Allemagne pour un fichier CAO/STL de couvercle de suppression de carter ventilateur 964/993 | C | Aucun fichier, cote ou licence dans la page; relancer l'auteur et clarifier le rôle de refroidissement avant usage |
| `SRC-RENNLIST-993-ALTERNATOR-INSULATOR-PHOTOGRAMMETRY` | Tentative d'un amateur : environ 100 photos pour reconstruire un isolant d'alternateur 993 cassé; modèle jugé trop irrégulier et incomplet | C | Aucun fichier ni cote; le retour d'expérience favorise une mesure directe et une reconstruction CAO, pas une photogrammétrie non contrôlée |
| `SRC-PFF-993-CARRERA-4-LETTERING-POSITION` | Mesures allemandes de position et largeur des monogrammes Carrera/Carrera 4 sur deux voitures 993 | C | Mesure communautaire sans instrument ni répétition; utile pour restauration visuelle, pas pour fabriquer une pièce ou généraliser au 4S |
| `SRC-RENNLIST-993-DASHBOARD-LIGHTING-DIMENSIONS` | Ouverture de tableau de bord estimée à environ 19 × 31 mm, ou façade d'un boîtier de switch à environ 17 × 28 mm | C | Valeurs déclarées par un propriétaire; aucun instrument, datum ou répétition; piste à remesurer pour la console, sans preuve d'ajustement |
| `SRC-PFF-993-INSTRUMENT-INNER-RING-LEAD` | Fil allemand recherchant les cotes ou une source pour les fines bagues intérieures chromées des instruments 993 | C | Aucune cote ni CAO dans le fil; obtenir une bague déposée et relever ses diamètres, largeur, épaisseur et profondeur |
| `SRC-PFF-993-OPTION490-SPEAKER-MEASUREMENT-LEAD` | Fil allemand récent : demande de cotes pour les haut-parleurs M490; retours d'installation Pioneer, Option AIR-130 et Ampire CP460 dans les points d'origine | C | Aucun tableau de cotes, instrument, profondeur ou répétition; contacter les propriétaires et mesurer par variante audio |
| `SRC-RENNLIST-993-RS-HOT-AIR-BYPASS-TUBE-CAD-LEAD` | Fil d'amateur : réduction d'environ 2 pouces d'un conduit d'air chaud RS, réemploi d'un manchon OEM et proposition d'une reconstruction CAO/imprimée autour de la réf. 99321134601 | C | Valeur approximative sans instrument ni fichier; mesurer les extrémités, vérifier débit/température et obtenir l'autorisation de l'auteur avant toute réutilisation |
| `SRC-CULTS-993-SEAT-HINGE-COVER-CAD` | STL commercial d'une plaque de cache de charnière de siège avant annoncée pour 993/964/968/944/928/924, auteur FIBERcraftENGINEERING, design 2192556 | D | Page détaillée inaccessible; dimensions, ajustement, fichier source et licence de redistribution non vérifiés; acheter légalement, mesurer sur le siège exact et ne pas extrapoler aux fixations ou à la sécurité du siège |
| `SRC-HUMFWORKS-993-PARTS` | Fabricant : clip de téléphone 993/964 tardive, obturateurs de tableau de bord en trois tailles et bouchon d'essuie-glace 964/993 avec détails de montage | C | Aucun plan, scan, CAO, cote, tolérance ou contrôle indépendant; acheter un échantillon et demander les droits avant toute mesure ou réutilisation |
| `SRC-VAGBOARD-993-LOCK-COVER-FIT` | Forum germanophone : cache-serrure Porsche réf. 993 537 613 00 01C, adaptation légère des ergots et montage rapporté dans des serrures VW | C | Aucun plan, scan, cote, instrument, répétition ou licence; obtenir un échantillon et vérifier séparément la géométrie et l'interchangeabilité |
| `SRC-FVD-993-EXHAUST-TIPS-DIMENSIONS` | Fabricant allemand : embouts d'échappement inox ovales pour 993 étroit C2/C4/RS, enveloppe annoncée 120 × 85 mm | C | Enveloppe commerciale sans cotes d'interface, entraxe, épaisseur, tolérance ou mesure indépendante; zone chaude et vibratoire à caractériser sur échantillon |
| `SRC-ASTROLLCAGES-993-LASER-SCANNED-CAGE` | Fabricant : cage 993 annoncée conçue à partir d'un laser scan 3D, acier E355 de 40 mm et conception selon l'Annexe J FIA | D | Aucun nuage, CAO, résolution, rapport ou droit de réutilisation; structure de sécurité à ne pas reproduire sans ingénierie et validation dédiées |

Ces fils confirment une demande réelle pour les petites interfaces intérieures,
mais montrent aussi que le prototype d'atelier est une étape distincte de la
géométrie nominale : plusieurs versions ont été imprimées avant d'obtenir un
ajustement acceptable. Aucun fichier tiers ne doit entrer dans le dépôt sans
licence explicite, auteur identifié et comparaison à la pièce d'origine.

### Mesure allemande à contradiction interne

`SRC-PFF-993-AC-BELT-DIMENSIONS` rapporte, sur un même échange, une courroie de
climatisation 13 × 1085 qui ne monte pas, une 13 × 1100 qui serait ajustée, et la
référence Porsche 999 192 363 50 donnée comme 12,5 × 1085 pour 993 contre
13 × 1085 pour 964. Une flèche d'environ 15 mm est également mentionnée.

Cette source est utile pour détecter une confusion de référence ou de variante,
pas pour publier une cote : la contradiction doit être résolue par la pièce,
la variante et une documentation officielle avant toute décision.

### Cotes de caisse et demande de mesure de châssis

| Fiche | Résultat | Niveau | Décision |
|---|---|---|---|
| `SRC-RENNLIST-993-BODY-DIMENSIONS-PDF` | Plusieurs pièces jointes indexées : « body dimensions small » (1,06 MB), « body measurement » (773,6 kB) et « temp body structure dimensions » (1,0 MB); schémas et points en millimètres annoncés | C | Fichiers et provenance non vérifiés, accès 403; obtenir légalement puis comparer à une documentation officielle ou une mesure directe |
| `SRC-PFF-993-BODY-DIMENSIONS` | Dimensions extérieures rapportées par variante : Carrera 1735 mm de large, S/Turbo 1795 mm, GT2 1855 mm, longueurs 4245 mm | C | Référence d'encombrement; les points de mesure et les variantes doivent être confirmés |
| `SRC-ASTRA-993-TYPE-APPROVAL-DIMENSIONS` | Typenschein suisse officiel en allemand pour un coupé Carrera 993 : 4245 mm de longueur, 2272 mm d'empattement, 1735 mm de largeur et 1300 mm de hauteur, 1285 mm avec châssis sport | A déclaré | Référence d'homologation de l'enveloppe du véhicule; droits de redistribution à confirmer et aucune cote d'interface ou tolérance de fabrication |
| `SRC-PFF-993-REAR-SUBFRAME-MEASUREMENT-REQUEST` | Liste explicite des distances à mesurer sur le berceau arrière, mais aucune réponse chiffrée sur la page | D | Relancer un propriétaire avec véhicule sur pont; ne pas traiter la demande comme un plan |
| `SRC-RENNLIST-993-RIDE-HEIGHT-MEASUREMENTS` | Points de référence sous caisse et valeurs RoW Sport 144 +/- 10 mm avant, 127 +/- 10 mm arrière, avec limites d'écart | C | Repères et valeurs communautaires à confirmer; utile pour caler une campagne de mesure, pas géométrie de pièce ni réglage libérable |

Le PDF Rennlist est une piste potentiellement importante pour les points de
référence, mais son statut de droit et son origine technique ne sont pas établis.
Les dimensions PFF sont utiles pour repérer une erreur de variante, pas pour
reconstruire une surface. Le berceau arrière relève en outre d'une zone liée à
la suspension : il reste hors périmètre de fabrication sans revue d'ingénierie.

### Prestataires CT, laser et scan-to-CAD

| Fiche | Capacité documentée | Limite actuelle |
|---|---|---|
| `SRC-FREEFORM-GMBH-CT-LASER-RE` | Prestataire allemand : CT d'objets jusqu'à 300 × 300 × 400 mm, NanoCT annoncée à 1 µm ou moins, rapports de mesure, scan-to-CAD; scanner laser de ligne sur MMT pour pièces jusqu'à 1,6 m | Capacités commerciales déclarées, aucun scan 993 public; le laser n'est pas du LiDAR de véhicule |
| `SRC-A-CONCEPTS-SCAN-FEM-SERVICE` | Scan mobile, préparation CAO et FEM; référence allemande mentionnant un moteur de 993 Turbo dans un projet 917 | Projet confidentiel, aucune géométrie 993 publiée ni précision de livraison contractuelle |
| `SRC-OTTO-MODELS-993-LASER-SCAN` | Témoignage d'un scan laser d'une 993 Carrera pour préparer un modèle réduit Otto | Pas d'échelle, de nuage de points, de précision ou de droits de réutilisation |
| `SRC-FABSPEED-993-LASER-SCAN-EXHAUST` | Fabricant affirmant avoir scanné au laser les plateaux moteur, silencieux et catalyseurs OEM 993 avant conception CAO d'un X-pipe | Aucun nuage de points, CAO, tolérance ou rapport d'essai publié |
| `SRC-SCHIMMEL-993-SCAN-SERVICE` | Prestataire citant la Porsche 911 (993) parmi ses campagnes de scan laser de véhicules, panneaux et intérieurs | Aucun livrable 993 public; instrument, précision et licence à définir par devis |
| `SRC-SCHONER-993-GT2-LIDAR` | Page technique désormais relue directement : revendication d'un scan LiDAR haute fidélité et accès annoncé à des blueprints/CAO d'une 993 GT2 EVO II | Projet électrique fortement modifié; aucun fichier public, échelle, rapport ou droit de réutilisation confirmé |
| `SRC-KUKUK-CLASSIC-CAR-3D-SCAN` | Bureau allemand : nuage de points, modèle 3D, dimensionnement, scan mobile et 3D-Röntgen annoncés pour carrosseries et pièces de rechange | Aucun jeu 993 public, rapport, sortie CT/scan ou licence; précision de 0,01 mm annoncée pour l'équipement, non pour une 993 |
| `SRC-CMA-MOBILE-3D-VEHICLE-METROLOGY` | Métrologie allemande mobile ou en laboratoire : nuage de points, mesh et rétroconception vers STEP/IGES/CATIA/SOLIDWORKS/NX/Creo, avec rapport PDF; systèmes ISO 17025 annoncés | Aucun jeu 993 public; 0,010–0,012 mm annoncés pour les équipements, à confirmer par rapport et devis |
| `SRC-ASEC-AUTOMOTIVE-SCAN-RE` | Prestataire allemand : scan optique mobile ATOS/TRITOP, CT industriel pour géométries cachées, mesures, rapports et rétroconception vers STL/OBJ/PLY/CAD | Aucun jeu 993 public; demander méthode, fixations, incertitudes, analyse d'erreurs, datums et droits de réutilisation |
| `SRC-PCM-SCAN-TRACEABLE-METROLOGY` | Prestataire allemand : lasertracker AT960 + scanner AS1, contrôle GD&T et reconstruction vers E57/PLY/STL/OBJ/STEP/IGES; incertitude système annoncée ±15 µm + 6 µm/m selon ISO 10360-10 | Aucun jeu 993 public; valeur annoncée du système, pas résultat sur 993; datums, répétitions, surfaces cachées et licence à contracter |
| `SRC-3D-OLDTIMER-GERMANY-RE` | Fabricant allemand annonçant scan-CAD-impression, contrôle d'ajustement dans l'assemblage et test de cycles; exemple Porsche 924/911 | Aucun cas 993 ni CAO public; exemple de support de conduite de carburant hors périmètre sans revue |
| `SRC-LMS-993-GT2-EVO-WHOLE-CAR-SCAN` | Vidéo documentant le scan 3D complet d'une 993 GT2 EVO modifiée pour préparer une transformation | Aucun nuage, mesh, CAO, échelle, précision ou droit de réutilisation; piste de contact, pas géométrie OEM |
| `SRC-ED24-GERMANY-SCAN-RE` | Prestataire allemand : scan de pièce, STL/OBJ, reconstruction CAO/STEP et précision annoncée de 0,1 mm | Exemple public hors 993; précision déclarée, aucun rapport 993 ni licence de livrable |
| `SRC-3DPADELT-GERMANY-CT-LASER-RE` | Prestataire allemand : scan optique/laser, photogrammétrie, lasertracker et CT; nuages E57/LAS/LAZ, mesh et CAO STEP/IGES/DXF | Aucun cas 993 public; précision dépendante de l'objet, du volume et de la méthode; aucun livrable ou droit 993 vérifié |
| `SRC-3D-DRUCK-SERVICE-FRANKFURT-RE` | Prestataire allemand : scan et rétroconception internes, archivage numérique, reproduction d'oldtimer, volumes d'impression jusqu'à 800 × 800 × 1000 mm; tarif CT annoncé à partir de 99 € | Aucun cas 993 public, CT/LiDAR non identifié et performances déclarées sans protocole; demander un devis traçable et les droits des livrables |
| `SRC-PROLASERTEC-GERMANY-3D-SCAN-CAD` | Prestataire allemand : projection de franges, nuage de points, mesh et options STL/STEP/DXF; pièces jusqu'à 300 × 300 × 300 mm, tarif annoncé à partir de 69 € | Aucun cas 993 public ni rapport; 0,04 mm annoncé pour l'équipement, à confirmer par devis, rapport et droits de la CAO |
| `SRC-JOCHAM-OLDTIMER-SCAN-RE` | Prestataire allemand : scan d'oldtimer, CAO STEP/IGES et reconstruction pour moulage; précision annoncée 0,2 mm sur surfaces libres et 0,05 mm sur surfaces réglées | Aucun cas 993 public; valeurs commerciales déclarées, à confirmer par rapport et contrat |
| `SRC-PROSCAN3D-GERMANY-SCAN-RE` | Service allemand : STL brut ±0,10 mm, STL traité ±0,05 mm et CAO STEP ±0,05 mm annoncés; option de droits exclusifs | Aucun cas 993 public; précision dépendante de la pièce et du procédé, livrable et droits à contractualiser |
| `SRC-SCANIT3D-GERMANY-SCAN-METROLOGY` | Prestataire allemand : scan de 3 à 30 000 mm, scanners Creaform, rétroconception CAO et rapports de contrôle | Aucun cas 993 public; performances annoncées par système, pas résultat sur une pièce 993 |
| `SRC-LASER3DSCAN-GERMANY-RE` | Prestataire allemand : scan laser 5 mm–4 m, mesh STL/OBJ/PLY, CAO paramétrique STEP/IGES et archivage client; prix indicatifs à partir de 70 € HT / 350 € HT | Aucun cas 993 public; 0,02 mm est un meilleur cas déclaré, la page indique une tolérance pratique d'environ ±0,03 à ±0,1 mm et exclut les géométries internes cachées |
| `SRC-RICHTSATZ-MIETEN-993-CELETTE` | Loueur allemand listant le jeu Celette `564.330`, « 911 Carrera Typ 964 / Zusatz 993 » | Aucun plan de piges, coordonnée ou certificat publié; piste de montage et de mesure directe à contractualiser |
| `SRC-KFZ-GUTACHTER-BERLIN-993-3D-BODY-MEASUREMENT` | Bureau allemand montrant une référence 993 Targa et annonçant la mesure 3D de carrosserie | Aucun nuage, rapport, repère constructeur, incertitude ou valeur 993 public; expertise de sinistre à distinguer d'une CAO nominale |
| `SRC-TZR-PAUTER-993-CONNECTING-ROD-DIMENSIONS` | Fiche fabricant allemande : bielle 993/993 Turbo avec cotes, tolérances, masse, matériau et contrôles annoncés | Données produit sans plan CAO ni mesure indépendante; pièce fortement chargée, interdite de reproduction sans revue d'ingénierie et validation fatigue |
| `SRC-PARTWORKS-993-BRAKE-DISC-DIMENSIONS` | Catalogue allemand : disque 993 Turbo avant annoncé 322 × 32 × 72 mm, et disques arrière RS/WTL/Turbo et Carrera annoncés respectivement 322 × 28 × 68 mm et 299 × 24 × 65 mm; centrage 103 mm et cercle 130 mm | C | Cotes commerciales sans plan ni mesure indépendante; frein critique, aucune fabrication ou libération sans revue d'ingénierie et validation approuvée |

### Nouvelles pistes allemandes et communautaires

| Fiche | Résultat | Niveau | Décision |
|---|---|---|---|
| `SRC-ROADSTER-FASHION-993-HEADLAMP-HOOK` | Crochet de réparation imprimé en aluminium ou inox pour le ressort de maintien du phare 993 | B déclaré | Pas de cote, CAO, tolérance ou qualification de collage; demander un échantillon et contrôler le réglage du phare |
| `SRC-LT3D-993-HEATER-KNOB` | Molette de chauffage 993/964/944/968 imprimée en 3D, référence 94465320500 | B déclaré | Compatibilité, matériau exact et tolérance non publiés; piste pour une mesure directe d'une pièce intérieure |
| `SRC-DTW-993-SMARTPHONE-HOLDER` | Support de smartphone remplaçant le cendrier, en plastique renforcé carbone, pour 993 | B déclaré | Produit commercial sans fichier ni interface cotée; benchmark et contact seulement |
| `SRC-FVD-993-SMARTPHONE-HOLDER-DIMENSIONS` | Fiche allemande du support DTW : encombrement déclaré 160 × 100 × 70 mm et masse 0,32 kg | C | Enveloppe produit, pas cotes d'interface ni mesure indépendante; aucune CAO ni tolérance publiée |
| `SRC-FVD-993-DOOR-HANDLE-DIMENSIONS` | Fiche allemande d'un jeu de poignées aluminium pour 993 : encombrement déclaré 108 × 45 × 27 mm et masse 0,18 kg | C | Dimensions du produit vendeur, sans datums, tolérance, CAO ou mesure indépendante; obtenir un échantillon avant comparaison à l'OEM |
| `SRC-FVD-993-RADIO-DASHBOARD-COVER-DIMENSIONS` | Cache radio aftermarket sans ouverture de switch pour 964/993 : encombrement déclaré 187 × 58 × 28 mm, masse 0,13 kg | C | Dimensions probablement d'encombrement produit, pas interface; acheter un échantillon et mesurer avant comparaison au switch blank |
| `SRC-PORSCHE-CLASSIC-PCCM-993-DIMENSIONS` | Page officielle Porsche : unité PCCM 1-DIN compatible 993, dimensions d'encombrement 187,5 × 58 × 170 mm, référence 91164559000 | A | Cote du boîtier d'un appareil, pas cavité ni fixation de la console; aucun plan d'interface ou CAO; référence de contrôle seulement |
| `SRC-FVD-993-HOOD-EMBLEM-DIMENSIONS` | Jeu d'emblème/support de capot compatible 993 : taille déclarée 67 × 51 mm et avertissement d'ajustement du support | C | Déclaration commerciale sans plan ni tolérance; utile pour une finition visuelle seulement, à contrôler sur échantillon |
| `SRC-FVD-993-ENGINE-INSULATION-COVER-DIMENSIONS` | Cache GFK aftermarket pour bord de matelas d'insonorisation moteur 993 : encombrement déclaré 840 × 100 × 50 mm, masse 0,24 kg, cinq boutons de pression | C | Enveloppe produit sans clips, perçages, rayons, tolérance ou caractérisation thermique; obtenir un échantillon avant toute reconstruction |
| `SRC-FVD-993-INLET-VALVE-DIMENSIONS` | Fiche allemande FVD : soupape d'admission 993 C2/C4 et Turbo annoncée avec queue de 8 mm, tête de 49 mm et masse de 120 g; encombrement 50 × 110 × 50 mm | C | Déclaration commerciale sans longueur fonctionnelle, matière, traitement, tolérances, plan ou mesure indépendante; chaîne de distribution fortement chargée, aucune reproduction ou libération sans revue d'ingénierie et validation fatigue |
| `SRC-PARTWORKS-993-EXHAUST-VALVE-DIMENSIONS` | Catalogue allemand partworks : soupape d'échappement Carrera annoncée à 109 × 42,5 × 8 mm et soupape Turbo à 108,9 × 43,5 × 8 mm | C | Déclaration commerciale sans tolérances, matière, traitement, gorge, contrôle, plan ou mesure indépendante; chaîne de distribution fortement chargée, aucune reproduction ou libération sans revue d'ingénierie et validation fatigue |
| `SRC-PFF-993-WHEEL-EMBLEM-DIMENSIONS` | Fil allemand : emblème de cache de roue associé à une 993 annoncé à 35 × 46 mm | C | Déclaration communautaire sans instrument, orientation, répétition ou ajustement du cache; gabarit décoratif à vérifier sur échantillon, sans géométrie de roue ou de fixation déduite |
| `SRC-PFF-993-FRONT-BRAKE-CALIPER-PISTON-DIAMETERS` | Fil allemand : pistons d'étriers avant 993 standard et BiTurbo annoncés à 44 et 36 mm | C | Réponse non instrumentée, sans distinction de position ni tolérance; frein critique, piste documentaire uniquement et aucune fabrication ou libération sans revue et validation approuvée |
| `SRC-PORSCHE-993-DME-REFERENCE-SENSOR-GAP` | Document technique Porsche en allemand : écart capteur de régime/référence–couronne du volant moteur réglé à 1,0 ± 0,2 mm | A | Cote de réglage de service, sans plan de pièce ni datums complets; document sous droits, à utiliser pour contrôle et non pour reconstruire une interface sans vérification |
| `SRC-FVD-993-DOOR-TRIM-PANEL-DIMENSIONS` | Panneau de porte gauche 993 : dimensions produit déclarées 105 × 44 × 2 cm et masse 1,6 kg, avec nombreuses variantes listées | C | Encombrement commercial sans découpes, datums, tolérances ou CAO; commander un échantillon et relever l'interface OEM avant reconstruction |
| `SRC-CURBS-993-DOOR-PANEL-SPEAKER-CUTOUT-DIMENSIONS` | Fabricant allemand : découpes déclarées de 154 mm pour le haut-parleur principal et 68 mm pour le tweeter sur panneaux RS compatibles 993/993 Turbo/GT | C | Cotes de configuration aftermarket/RS, pas ouverture OEM; acheter et mesurer un panneau avant usage |
| `SRC-TUERPAPPEN-993-DOOR-PANEL-3MM` | Fabricant allemand : bases de panneaux 993 annoncées en plaque de 3 mm, découpes configurables et préparation pour haut-parleurs de 16 cm | C | Épaisseur et configuration d'un panneau aftermarket, sans cotes d'interface ni CAO; commander un échantillon et relever les perçages avant reconstruction |
| `SRC-JEHNERT-993-DOORBOARD-TECHNICAL-DATA` | Brochure allemande Jehnert pour doorboards 993 : haut-parleur nominal 200 mm, tweeter 26 mm et léger agrandissement de la tôle intérieure | B déclaré | Dimensions de composants aftermarket, pas ouvertures ou entraxes OEM; brochure sous droits et aucune CAO redistribuable |
| `SRC-CARPASSION-993-DOOR-SPEAKER-ADAPTATION` | Retour de forum 964/993 : passage d'un haut-parleur 13 cm à 16 cm et quatre trous d'adaptation de 2,5 mm | C | Adaptation décrite sur 964, transposition 993 à confirmer; pas de datum, profondeur, répétition ni fichier CAO |
| `SRC-CK-CABRIO-993-STYLE-CONVERTIBLE-MEASUREMENTS` | Fabricant allemand : différence de rayon annoncée de 34 mm entre architectures 964/G-modèle et 993, avec détails de débord et de joint de capote | B déclaré | Mesures d'une adaptation aftermarket, pas d'une capote OEM; utile pour séparer les variantes, à vérifier sur véhicule et patron |
| `SRC-PARTWORKS-993-SWITCH-BLANK-OEM` | Fiche allemande d'une Schalterblende OEM Porsche refs 9936135230001C / 993.613.523.00, fitment 993 1994–1998, plusieurs variantes | B | Page sans cote, scan, CAO ni tolérance, actuellement indisponible; obtenir un exemplaire avant mesure |
| `SRC-PFF-993-TURBO-SEAT-CLIP-MEASUREMENT` | Fil allemand : fil d'acier de 1,5 mm et clip en S d'environ 10 mm pour coussin de dossier de 993 Turbo | C | Valeurs approximatives, sans instrument ni dessin; pièce de siège à vérifier avant toute reproduction |
| `SRC-993C2-993-SEAT-MOUNTING-DIMENSIONS` | Billet allemand : voie de siège 408 mm, plaques St37 de 5 × 30 mm, M8 × 20 et trou de 12 mm à 40 mm de l'extrémité | C | Adaptation 996-sur-993 C2, pas plan OEM; zone de fixation de siège soumise à revue et validation spécifiques |
| `SRC-PFF-993-CR21-RADIO-COVER-LEAD` | Fil allemand sur une cache manquante de radio CR-21; les membres proposent une découpe plastique ou une impression 3D | C | Aucune cote, référence, CAO ou fichier; piste de contact seulement |
| `SRC-PFF-993-PORSCHE-WHEEL-CERTIFICATE` | PDF allemand Porsche relayé par PFF : combinaisons de jantes et déports ET de 16 à 18 pouces, par variante | B déclaré | Référence de sécurité sous copyright; aucune fabrication ou libération de roue sans vérification dédiée |
| `SRC-PFF-993-FRONT-LID-SHEET-THICKNESS` | Fil allemand : épaisseur de tôle du capot avant estimée à environ 0,6 mm et peinture usine évoquée à 100–120 µm | C | Aucun instrument ni protocole; piste de comparaison sur échantillon, pas spécification de matériau ou de panneau composite |
| `SRC-SPORTWAGENDOKTOR-993-CLIMATE-FAN-MOUNT` | Cas de réparation d'une climatisation 993 où le support du ventilateur d'une unité Porsche est annoncé imprimé en 3D | B déclaré | Aucun fichier, cote, matériau ou droit; précédent de fabrication, pas géométrie réutilisable |
| `SRC-3DGO-993-964-CUP-HOLDER` | Modèle communautaire 993/964 indexé avec licence Public Domain annoncée; une archive secondaire donne aussi une photo de montage et une bbox | D | Licence primaire Printables et unités non vérifiées; ne pas redistribuer avant confirmation |
| `SRC-ARMYTRIX-993-UNDERBODY-SCAN` | Fabricant annonçant un scan 3D du soubassement 993 pour prototypage d'échappement | C déclaré | Aucun scan, CAO, résolution, alliage ou rapport; piste de contact, échappement soumis à fortes contraintes thermiques et vibratoires |
| `SRC-NIEDERHOF-993-POLYCARBONATE-MEASUREMENT` | Vitrages 993/GT2 fabriqués selon original, gabarit ou CAO; procédé annoncé : mesure, cintrage sur deux axes, recuit à 175 °C et traitement de surface | B déclaré | Pas de géométrie ni tolérance publiées; utile pour demander un gabarit ou une campagne de mesure, avec validation réglementaire séparée |
| `SRC-RENNLIST-993-JACKING-POINT-MEASUREMENT` | Un relevé communautaire annonce environ 235–240 mm et 275 ± 5 mm entre repères de levage sur un C2 | C | Relevé unique et repères ambigus; confirmer C2/C4 avec datums, répétitions et photos, sans usage pour une pièce de suspension |
| `SRC-RENNLIST-993-JACKING-POINT-DISCREPANCY` | Fil Carrera 4 : schéma annoncé à 1245 mm, calcul alternatif à 1195 mm et réponse à 52 pouces entre points avant/arrière | C | Valeurs contradictoires et repères non définis; contrôler sur véhicule avec datum et répétitions, sans usage pour une pièce structurelle |
| `SRC-THINGIVERSE-993-PHONE-MOUNT` | Support de téléphone 993/964; une archive secondaire confirme un STL déclaré CC-BY, anneau de compteur 82 mm et bbox 136,013 × 91,999 × 35,520 mm | D | Source primaire, licence et unités à confirmer; aucune déclaration d'ajustement ou de précision |
| `SRC-CELERITECH-KALMAR-993-PHOTOGRAMMETRY` | Echappement d'une base 993 capturé par photogrammétrie/scan 3D, reconstruit en CAO et contrôlé par laser | B déclaré | Véhicule modifié, données propriétaires et aucune précision publiées; référence de méthode, pas géométrie OEM |
| `SRC-PFF-993-TARGA-ANTENNA-HOLE-MEASUREMENT` | Trou de pied d'antenne rapporté à presque 19 mm sur une voiture probablement déjà modifiée; origine estimée à 16 mm, avec languette anti-rotation | C | Distinguer la modification de la cote OEM; remesurer sur une caisse non modifiée avant toute CAO |
| `SRC-PFF-993-PASSENGER-FOOTWELL-COVER-DIMENSIONS` | Cache de support téléphone identifié par la référence 964 552 133 00; partie plastique estimée à environ 100 × 80 mm | C | Approximation sans épaisseur ni clips; obtenir un exemplaire et mesurer avant toute reconstruction |
| `SRC-FSH-993-DASHBOARD-TRIM-DIMENSIONS` | Garniture aftermarket 964/993 : entraxe radio annoncé à 130 mm, découpe environ 95 × 42 mm et bague optionnelle Ø55 mm | C | Cotes du produit Singer Style, pas de l'OEM; adaptation airbag et interfaces à vérifier sur échantillon |
| `SRC-TECHART-993-REAR-SPOILER-MOUNTING-MANUAL` | Notice allemande TECHART : distinction Carrera/Turbo, kit de montage 093.100.850.009 pour Carrera, points de fixation et câblage du feu stop | A | Notice fabricant sans coordonnées cotées; spoiler soumis aux efforts aérodynamiques, aucune géométrie de fabrication ou modification sans validation |
| `SRC-TECHART-993-REAR-SPOILER-I-DRILLING-MANUAL` | Notice allemande TECHART : gabarit de perçage du spoiler I 993, perçage de 10 mm et couple de 1,3 Nm pour la fixation du feu stop | A | Instructions d'accessoire, sans entraxes ni coordonnées OEM; zone aérodynamique et couvercle mobile, aucune modification sans validation |
| `SRC-PORSCHE-993-SPOILER-TEILEGUTACHTEN` | Dossier Porsche/TÜV allemand : combinaisons homologuées d'Aerokit 993, références et exigences de montage pour Carrera/RS | A | Document officiel sans coordonnées CAO; droits de reproduction restreints et aucune modification de spoiler sans contrôle de variante et validation |
| `SRC-PORSCHE-993-AIR-FILTER-TEILEGUTACHTEN` | Dossier Porsche/TÜV allemand : boîtier de filtre à air perforé 993, réf. 993.110.030.06 et variantes de type/modèle | A | Référence de configuration sans cotes ni géométrie; document sous droits, aucune reconstruction à partir du texte seul |
| `SRC-PFF-993-OVERALL-WIDTH-MIRRORS` | Mesure communautaire allemande : largeur hors tout d'une 993 avec rétroviseurs annoncée à environ 183,2 cm | C | Repères, état des rétroviseurs, instrument et répétitions non établis; contrôler sur véhicule, sans la confondre avec la largeur de caisse homologuée |
| `SRC-OLDTIMER-ERSATZTEILE24-993-SWITCH-RING-DIMENSIONS` | Fiche allemande : bague de commutateur 911/964/993 annoncée Ø30,5 mm extérieur, profondeur 10,5 mm, Ø23 mm avant et Ø28 mm arrière | C | Cotes déclarées d'une reproduction commerciale, sans plan ni mesure indépendante de l'ouverture OEM; acquérir un échantillon avant comparaison |
| `SRC-FVD-993-CARBON-SWITCH-PANEL-DIMENSIONS` | Fiche allemande : Schalterblende carbone 964/993 annoncée 124 × 75 × 47 mm, 0,02 kg | C | Encombrement d'un produit commercial recouvert de carbone, sans cotes d'interface ni plan OEM; mesurer un échantillon avant reconstruction |
| `SRC-FVD-993-FRONT-IMPACT-TUBE-DIMENSIONS` | Fiche allemande FVD : tube d'impact avant aluminium 993 annoncé 139 × 100 × 53 mm et environ 0,14 kg | C | Dimensions commerciales sans plan ni mesure indépendante; élément de protection crash, aucune substitution sans revue d'ingénierie et validation dédiée |
| `SRC-KFZ-KAUERT-993-REAR-CONTROL-ARM-DIMENSIONS` | Fiche allemande : bras arrière 993 reconditionné annoncé à 380 mm de longueur et 340 mm d'entraxe | C | Dimensions commerciales sans datums, tolérances ni méthode; suspension, aucune substitution sans revue d'ingénierie et validation dédiée |
| `SRC-FVD-993-LIGHT-SWITCH-SYMBOL-CAP-DIMENSIONS` | Fiche allemande : capuchon de symbole d'interrupteur 964/993 annoncé 25 × 25 × 5 mm, 0,02 kg, clipsé sur le bouton | C | Enveloppe commerciale sans datum, tolérance, plan ou mesure indépendante; obtenir un échantillon avant comparaison à l'OEM |
| `SRC-RENNLIST-993-CONSOLE-SWITCH-HOLE-DIMENSIONS` | Relevé communautaire : ouverture de console d'une 993 1997 env. 17,0 × 27,9 mm et cache env. 16,2 × 27,4 mm | C | Mesure unique sans instrument, tolérance ni répétition; page bloquée, remesurer sur la variante exacte avant CAO |
| `SRC-TECHART-993-BKS-CUTTING-TEMPLATE` | Gabarit allemand TECHART pour 993 BKS : contour de découpe, repère de bord avant et échelle imprimée de 100 mm | A | Le produit cible, les datums, coordonnées et tolérances ne sont pas explicités; impression à taille réelle obligatoire, document sous droits et aucune géométrie redistribuable |
| `SRC-RENNLIST-993-3D-PRINTED-DIY-BITS` | Fil d'amateurs sur des pièces 993 imprimées : cadres de haut-parleurs, gabarits de pare-brise, bagues de siège et support de gobelet | D | Page bloquée, fichiers et licences non vérifiés; liens vers Thingiverse/Printables à contrôler individuellement, aucun mesh ne remplace une mesure OEM |
| `SRC-FVD-993-A-PILLAR-FAIRING-DIMENSIONS` | Fiche allemande FVD : déflecteurs de gouttière 993 annoncés 550 × 80 × 50 mm et 0,29 kg | C | Encombrement d'un produit GFK aftermarket, sans plan, datums ni tolérances; modification aérodynamique à traiter comme benchmark, pas comme géométrie OEM |
| `SRC-CLASSICPARTS-993-WINDOW-SWITCH-DIMENSIONS` | Fiche allemande : interrupteur de lève-vitre 964/993 annoncé 35 × 35 × 60 mm et 0,02 kg | C | Page détaillée expirée lors de l'accès; vérifier si les dimensions concernent la pièce ou l'emballage, sans plan ni tolérance et sans mesure indépendante |
| `SRC-PARTWORKS-993-THROTTLE-LINKAGE-BUSHING-DIMENSIONS` | Catalogue allemand : bague de tringlerie d'accélérateur 911/964/993 annoncée ID 8,15 mm, OD 12,15 mm et hauteur 8 mm | C | Dimensions commerciales déclarées, sans datums, tolérances, matériau, CAO ou mesure indépendante; acquérir un échantillon et vérifier la tringlerie avant toute reconstruction |
| `SRC-PFF-993-ALARM-MODULE-MEASUREMENTS-TOOL` | Propriétaire allemand : tableau Excel de valeurs mesurées sur le boîtier alarme/ZV 993 et outil d'ouverture imprimé, STL proposé en privé | C | Pièce jointe, protocole, cotes et droits non vérifiés; contacter l'auteur avant toute acquisition, sans transformer la mesure électrique en géométrie |
| `SRC-PFF-993-INSTRUMENT-GLASS-THICKNESS` | Fil allemand : épaisseur du verre des instruments d'un 993 annoncée à environ 3,8 mm | C | Mesure unique sans instrument, zone, tolérance ni répétition; obtenir un verre déposé et remesurer avant toute reproduction |
| `SRC-PFF-993-CASSETTE-CONSOLE-3D-PRINT` | Propriétaire allemand annonçant une console de rangement imprimée après retrait de la Fischer C-Box d'un 993 Cabriolet | C | Aucun fichier, cote ou essai publié; contacter l'auteur et remesurer les interfaces de la console avant toute CAO |
| `SRC-PORSCHE-ORIGINALE-993-PRODUCT-DIMENSIONS` | Catalogue allemand Porsche Classic : nappe d'isolation 1 000 × 500 × 2,3 mm et bague 12 × 14 × 15 mm pour des références 993 | A déclaré | Cotes de fiche constructeur, non plan d'interface ni mesure indépendante; PDF sous droits, conserver la référence et l'URL seulement |
| `SRC-ELFERLISTE-993-STEERING-WHEEL-DIAMETERS` | Fil allemand : volant de série annoncé à 380 mm, Momo D36 mesuré à 360 mm et Prototipo à 350 mm | C | Mesures communautaires sans instrument, référence exacte, tolérance ni répétition; direction/airbag, aucune fabrication sans revue d'ingénierie |
| `SRC-THINGIVERSE-993-RS-MOMO-HORN-RING` | Fichier Thingiverse indexé pour volant Momo de 993 RS : trou 52 mm, Ø extérieur 59 mm et saillie 3 mm annoncés | D | Licence et mesure indépendante non vérifiées; élément lié à la direction, aucune libération sans revue d'ingénierie |
| `SRC-PARTWORKS-993-WHEEL-CENTER-CAP-DIMENSIONS` | Fiche allemande partworks : cache-moyeu Porsche 993 réf. 9933613030761M annoncé en plastique, Ø extérieur 76 mm, Ø intérieur 60 mm et hauteur 46 mm | C | Cotes commerciales sans plan, datums, tolérances, méthode ou mesure indépendante; acquérir et mesurer un échantillon avant toute reconstruction, sans conclure sur la roue ou sa fixation |
| `SRC-FVD-993-GT2-STEERING-WHEEL-DIMENSIONS` | Fiche allemande FVD : volant GT2 pour 993 annoncé Ø350 mm, poignée Ø30 mm, dish 70 mm et masse 1,157 kg | C | Déclaration commerciale sans plan, entraxe, tolérance ni essai; pièce de direction/airbag annoncée sans TÜV, aucune reproduction ou libération sans revue d'ingénierie et validation réglementaire |
| `SRC-NETZWERK-9ELF-964-993-BUMPER-BRACKET-DIMENSIONS` | Fabricant allemand : supports de pare-chocs 964/993 annoncés avec plaque de base 10 mm, paroi de tube 5 mm et diamètre de tube 35 mm | C | Dimensions commerciales sans plan, datums, tolérances ni calcul; pièce liée au crash, aucune reproduction ou substitution sans revue d'ingénierie et validation dédiée |
| `SRC-PFF-993-SUNROOF-DEFLECTOR-REPAIR-LEAD` | Fil PFF allemand : référence 911 564 127 00 pour l'escamoteur de déflecteur de toit ouvrant et retour de remplacement réussi | D | Piste amateur sans cote, instrument, CAO, scan ou licence; obtenir une pièce déposée et mesurer avant toute reconstruction |
| `SRC-BMB-GERMANY-CT-RE` | Laboratoire allemand BMB : trois configurations CT publiées, de 7 µm à 0,2 mm, pièces jusqu'à 3 500 × 2 000 mm et 200 kg, reconstruction de surfaces et STL annoncées | B | Capacités de prestation, pas cas 993 ni données ouvertes; demander incertitude, datums, format et droits avant acquisition |
| `SRC-HACHTEL-BASIC-CT-SCAN` | Offre allemande de Basic Scan CT pour petites pièces : volume annoncé Ø180 × 180 mm, sortie voxel, STL optionnel, 99 € | C | Aucun nettoyage, segmentation, résolution voxel, incertitude ou licence de réutilisation; piste pour cache polymère, à compléter par une métrologie contrôlée |
| `SRC-FRAUNHOFER-ROBOCT-LARGE-PARTS` | Fraunhofer IIS : RoboCT robotisé pour grandes pièces automobiles, dont portes, hayons et structures latérales, avec régions d'intérêt et microtomographie | B | Piste de recherche/prestation sans cas 993, fichier, rapport ni droits publiés; solliciter un protocole et un livrable contractuel |
| `SRC-VISION-METRIC-CT-DIGITIZATION` | Prestataire allemand : ZEISS METROTOM, volume 165 × 140 mm, voxel 65,3 µm ou 32,6 µm en haute résolution, STL et analyses annoncés | B | Capacité déclarée pour petites pièces, sans cas 993, incertitude, répétition ou licence de données; demander un échantillon et un rapport |

Ces résultats ajoutent des interlocuteurs et quelques candidats de petites
pièces, mais aucun ne constitue encore une mesure instrumentée ou une géométrie
réutilisable avec droits établis. La recherche allemande confirme surtout la
valeur d'une campagne directe sur une pièce intérieure déposée.

Ces prestataires fournissent une voie d'acquisition, non un corpus libre. Le
brief à envoyer doit exiger la variante et le numéro de pièce, les repères et
échelles, le rapport de métrologie, le format de sortie, les tolérances, le
traitement des surfaces cachées et une licence explicite pour la CAO livrée.
Pour une pièce creuse ou comportant des canaux internes, la CT est la méthode
pertinente; pour une carrosserie ou une grande interface extérieure, un scan
laser ou une photogrammétrie calée doit être complété par des références
dimensionnelles. Aucun LiDAR 993 public, étalonné et réutilisable n'a été trouvé
dans ce passage. Le site The Schöner est une exception apparente — une revendication
LiDAR explicitement trouvée — mais elle reste une piste sans donnée exploitable
ni droits vérifiés, sur une carrosserie GT2 EVO II électrifiée et non OEM.

## Lot 3 — Masses d'origine, par la recherche en allemand

`SRC-FEDERLEICHTE-ELFER-993-WEIGHTS` fournit ce qu'aucune source anglophone
n'avait donné : les masses des pièces d'origine du 993, face aux versions
allégées, matière par matière, sur trois pages — extérieur, intérieur, technique.

### Ce qui est directement exploitable par ce projet

Petites pièces d'habillage, non critiques, remplaçables à l'identique :

| Pièce | Origine | Allégée | Gain |
|---|---:|---:|---:|
| Baguettes de porte | 550 g | 170 g | 380 g |
| Planche de bord allégée | 2 100 g | 950 g | 1 150 g |
| Dessus de planche de bord | — | 290 g | — |
| Conduits d'air | — | 35 g | — |
| Cache de chauffage | — | 10 g | — |

Ce sont exactement les formes que le sélecteur fait remonter — `cover strip`,
`cover`, `insert` — et exactement le domaine où l'impression polymère est le bon
procédé.

### Ce que les gros chiffres cachent

Les plus grosses économies de ces tables ne sont **pas** des remplacements :

| Ligne | Gain affiché | Ce que c'est réellement |
|---|---:|---|
| Ensemble de ventilation | 11,4 kg | Dépose du chauffage, pas un remplacement |
| Siège course | 12,5 kg | Touche la retenue des occupants |
| Volant allégé | 1,9 kg | Suppression de l'airbag |
| Portes | 26 kg pièce | Perte des barres anti-intrusion et du vitrage |
| Pavillon | 19,5 kg | Panneau soudé structural |
| Roues, rotules | 1,5 à 3,3 kg | Classe présumée critique par `SAFETY.md` |

Une table de masses ne dit pas ce qu'on a le droit de retirer. Classer avant de
chiffrer, jamais l'inverse.

## Lot 4 — Pages rendues en JavaScript

Plusieurs sources ont été classées inexploitables le 28 août alors qu'elles
n'étaient que **rendues côté client** : la page répondait, mais son contenu
n'existait qu'après exécution du JavaScript. Ce n'est pas un refus, c'est un
problème de rendu — et la distinction change tout, parce qu'un refus se respecte
alors qu'un rendu se résout.

Vérification des `robots.txt` le 29 août 2026 :

| Source | Ce que dit son robots.txt | Verdict |
|---|---|---|
| `porsche.com` (catalogue Classic) | `User-agent: *`, n'interdit que `/api/`, `/search/`, `/login/` et des archives. **Aucun agent nommé.** | **Autorisé** |
| `wheel-size.com` | Autorise `/size/`, n'interdit que `/admin/`, `/api/`, `/data/` et les combinaisons de filtres | **Autorisé** |
| `newsroom.porsche.com` | `allow: /` | Autorisé, et déjà lisible |
| `pcss-tsi.porsche.com` | Le `robots.txt` lui-même renvoie 403 | Hôte fermé, hors de portée |
| `rosepassion.com` | `ClaudeBot` et `Claude-Web` en `Disallow: /` | **Refusé**, voir ADR 0003 |

Les deux premières lignes sont la trouvaille : **le catalogue de pièces officiel
Porsche et les données de jantes sont autorisés**, et leur contenu n'a pas été
lu uniquement faute de moteur de rendu.

### Test effectué le 29 août 2026, et son résultat

L'hypothèse était qu'un navigateur exécuté côté serveur lèverait l'obstacle. Elle
a été testée, sur compte Cloudflare, via Browser Run et son moteur Kitesurf.

**Le moteur fonctionne** : la page wheel-size a bien été rendue, 115 293
caractères extraits là où une requête simple n'en donnait presque rien.

**Et l'hypothèse est infirmée sur les deux cibles.**

| Cible | Résultat du rendu |
|---|---|
| `wheel-size.com` | La page rendue affiche `Bolt Pattern (PCD): -`, `Thread Size: -`, `Wheel Tightening Torque: -`. Ces valeurs **ne sont pas publiées**, elles n'étaient pas masquées |
| `porsche.com` catalogue | 722 caractères, les seules métadonnées, **identique avec Kitesurf et avec Chromium**. Le corps n'est servi à aucun navigateur sans tête |

Ce que cela enseigne dépasse ces deux pages : un champ vide dans une page peut
signifier « rendu plus tard » ou « jamais publié », et seuls un rendu réel les
distingue. Ici, c'était la seconde réponse dans les deux cas.

Browser Run ne change par ailleurs **rien** aux deux dernières lignes du tableau
précédent : un hôte qui renvoie 403 reste fermé, et un site qui refuse les agents
nommés continue de les refuser depuis n'importe quelle infrastructure.

## Reste à faire en Phase 1

- [x] Modèles 3D sous licence vérifiable — fichiers de pièces recensés par fiche;
      le scan GT2 reste à chaîne de droits imparfaite et aucun scan de carrosserie
      993 librement réutilisable n'a été trouvé. Voir les lots 2 et 5.
- [x] Classement par variante, année et disponibilité — chaque fiche porte la
      couverture, les variantes et le statut d'accès; les cas ambigus restent
      signalés dans les notes plutôt que fusionnés.
- [x] Pièces manquantes ou difficiles à obtenir — premier cas documenté par une
      source : le berceau moteur Turbo `993 115 021 53` n'a aucune alternative de
      rechange, le berceau tubulaire du marché spécialisé étant explicitement non
      Turbo. Les trois candidats polymères de la phase 2 restent, eux, choisis sur
      critères d'ingénierie et non sur une rareté documentée.
- [x] Évaluation croisée provenance, licence, précision, réutilisation — les
      294 fiches indiquent les droits connus, le niveau de preuve et les limites
      d'usage; aucune donnée non vérifiée n'est promue en géométrie de catalogue.

État : vingt candidats documentés, le seuil de sortie de phase est atteint en
nombre; le registre contient maintenant 294 fiches de sources valides. L'archive
Renn 3D Parts ajoute neuf pistes de fichiers STL publics, mais leurs licences
restent attachées à chaque fiche et leurs bboxes ne remplacent pas une mesure.
Les données du projet Porsche Fanatics et du manuel augmentent la couverture
technique, tandis que les nouveaux scans et sources allemandes augmentent la
couverture des pistes,
mais ne transforment aucun candidat en pièce libérable. Les sources sans accès
automatisé comptent comme candidats recensés, pas comme données exploitées. Deux
exemples, `SRC-TEILE-COM-993-ENGINE-CARRIER` et
`SRC-RENNLINE-TUBULAR-ENGINE-CARRIER`, refusent l'accès automatisé : ils comptent
comme candidats recensés, pas comme sources exploitées.
