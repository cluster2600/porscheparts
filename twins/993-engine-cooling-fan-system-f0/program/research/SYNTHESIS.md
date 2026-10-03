# Synthèse documentaire et décisions ouvertes

[Accueil recherche](README.md) · [Index avec sources et locators](source-index.json) · [Plan de validation](../VALIDATION_PLAN.md)

Cette synthèse résume les quatre lots livrés. Les identifiants renvoient aux
records originaux de l'index ; leurs réserves et niveaux d'accès priment sur
une lecture abrégée. Aucun dessin de pale, ajustement, régime sûr, courbe Turbo
complète ou qualification LPBF du rotor du projet n'a été établi.

## Identité et régimes

| Question | Résultat documentaire | Conséquence |
|---|---|---|
| Quel ventilateur 993 ? | PET993, planche 105-00, pages PDF 77–79 : Carrera `96410601531`, RS M64.20 `.40`, Turbo M64.60 `.21/.22`. ORIG05 reprend les familles. | Distinguer reconstruction Carrera et référence Turbo ; identifier la pièce physique. |
| Moyeu `96410605131` | ORIG05 et PET964 documentent les applications, dont Turbo M30.69/M64.50. | L'application catalogue ne fournit pas les cotes d'un moyeu aftermarket. |
| « 935 » identique 993 ? | PORSCHE935 / GEO-S008 distinguent plusieurs 935 ; la 935/78 combine culasses à eau et cylindres à air. | Les montages horizontaux et verticaux ne sont pas interchangeables par leur nom. Équivalence non démontrée. |
| Formation 964 | P10L : 12 pales, 17 aubes stator, rapport ventilateur 1,6. Rapports alternateur Tiptronic 2,23 → 2,68 distincts. | Toujours préciser l'axe du régime. |
| Débit Carrera | P10L : 1 010 L/s sans régime dans la table. GEO-S002 : 1 010 L/s à 6 000 tr/min vilebrequin Carrera, rapport environ 1,6. | 9 600 tr/min rotor est une conversion conditionnelle sans glissement ; ce point n'est pas une courbe Turbo. |
| Débit Turbo | ELFER993T / GEO-S005 : 1 210 L/s à 5 750 tr/min vilebrequin ; FORUMDIA et copies : 6 100 tr/min. Rapport 1,8 signalé par sources secondaires. | Conflit ouvert ; débit accepté pour la cible inconnu. |

FVD22 annonce 24,5 × 24,5 × 8,7 cm et 0,9 kg comme données commerciales de
produit. Ce ne sont pas une cote tolérancée de bout de pale et une masse
métrologique du rotor seul. Les 245 mm du modèle existant restent une hypothèse.
L'identité du scan et les interfaces physiques doivent être vérifiées.

## Produits et différences à préserver

| Sources | Donnée ou distinction | Réserve |
|---|---|---|
| AF01–AF03 EPS | Rotor aluminium moulé, 11 pales / 245 mm annoncés ; moyeu acier forgé. | « Forgé » ne décrit pas le rotor entier. |
| AF13, AF44 partworks | Ébauche 250 mm à usiner vers 245 ou 225 mm selon montage. | Ébauche et diamètre fini sont des états différents. |
| AF06–AF10 INDEX | Classic PRMA030 : 12 pales, 245 mm, environ 430 g, moyeu A7075. PRMA010 964/993 : environ 400 g, autres cotes inconnues. Carter 1 400 / 1 475 g selon page. | Variantes et masses contradictoires conservées ; référence du « 74 % » non établie. |
| AF04–AF05 | LN annonce un carter 6061 ; grade Rennline exact non établi. | Ne pas transférer la matière d'un carter au rotor ni inventer T6. |
| AF14–AF17 Carpoint | RSR 225 mm : carter magnésium 1 365 g, rotor 885 g ; carter aluminium distinct 1 850 g. Feuille : 244,5 mm / 11 pales et 254 mm / 12 pales. | Applications, datums et tolérances de la feuille à identifier. |
| AF17 | Saillie axiale rotor/carter 2 mm ; hauteurs d'alternateur et profondeurs de bague différenciées. | 2 mm n'est pas un jeu radial. Six trous à 60° ne donnent pas leur cercle de perçage. |
| AF20–AF26 | Torres, Spezialmotorer et Bailey décrivent des systèmes flat-fan ; FSH/TK/Design911 fournissent notamment entrée et rotor. | Sous-ensemble et conversion complète distincts. Même GTIN FSH/TK, masses 1 500 / 1 600 g : filiation et conflit conservés. |
| AF27 EB Motorsport | Entretien sur un banc : 1,5 hp à 4 000 et 32 hp à 12 000 tr/min ventilateur. | Protocole, définition hp, pression, débit, incertitude inconnus ; pas une courbe qualifiée ni une limite sûre. |
| AF28–AF29 Gunther Werks | Plus du double de volume d'air annoncé. | Comparateur et point absents ; 7 500 tr/min moteur n'est pas une limite rotor. |
| AF34–AF37 Classic Retrofit | 175 A : entraînement conventionnel/double ou RS ; 240 A : serpentine et tendeur recommandés. | **Aucun alternateur n'est sélectionné par l'utilisateur.** Interfaces à mesurer ; entretoises early 911 non transposables automatiquement. |

Dans ce périmètre, aucun fournisseur ne livre une carte pression–débit–puissance
complète avec protocole, une fatigue qualifiée du rotor cible ou un rotor AM
opérationnel qualifié. Les fiches ne sont ni des devis ni un droit de reproduire
la géométrie.

## Forums et filiation

Le [rapport multilingue](corpus/forums/multilingual_forum_research.md) et les
[lacunes d'accès](corpus/forums/coverage_and_gaps.md) distinguent témoignages,
mesures rapportées et tableaux repris. Les tableaux répétés de Bill Verburg,
notamment F01/F03/F04/F07, ne deviennent pas plusieurs confirmations
indépendantes. Les neuf points du [banc rapporté](corpus/forums/reported_bench_series.csv)
gardent leur axe de régime inconnu. Les récits de frottement, fissures ou
courroies préparent l'inspection ; ils ne donnent ni jeu nominal, ni grade
d'équilibrage, ni durée de vie du rotor cible.

## Mesures et calculs à préparer

Le [contrat de 104 paramètres](corpus/geometry/parameter-contract.json) conserve
les inconnues à `null`, les unités et les portes d'acceptation. La
[liste de mesures](corpus/geometry/measurement-checklist.md) définit le repère
fonctionnel : A = axe d'alésage, B = plan de montage, C = élément indexé. Deux
longueurs physiques indépendantes au minimum, trois de préférence, doivent
établir l'échelle. PCA globale et ICP automatique ne prouvent ni cet axe ni le
recalage relatif de l'arrière du scan.

GEO-S001 / SAE 920789 fournit un résumé primaire Porsche sur le refroidissement
et les différences de pression. Texte intégral et courbe exploitable non
vérifiés : acquisition légitime encore nécessaire. GEO-S024 indique une thèse
secondaire, environ 0,317 m³/s à 5 000 tr/min vilebrequin, sans validation
expérimentale de notre ventilateur.

GEO-S009 / GEO-S010 identifient **FAN-01**, benchmark axial indépendant à licence
CC BY 4.0 : rotor 495 mm, moyeu 248 mm, jeu 2,5 mm, neuf pales NACA4510,
1 486 tr/min, débit de conception 1,4 m³/s, cible 150 Pa et mesure rapportée
126,5 Pa / rendement 0,53. C'est une option pour vérifier une chaîne CFD avec des
mesures publiées. Ce n'est pas une géométrie Porsche ; aucun téléchargement de
ses archives ni calcul de ce benchmark n'est présenté comme exécuté ici.

GEO-S011, fiche EOS AlSi10Mg/M290/30 µm : données typiques, limite d'élasticité
verticale 230 MPa / horizontale 270 MPa, fatigue 110 MPa à 20 millions de cycles,
R = -1, éprouvettes tournées et état défini dans la fiche. Ce n'est ni un
admissible de pale ni une qualification ZRapid. Les calculs LPBF du projet
gardent leur propre carte process et leurs limites.

ISO/AMCA GEO-S012–GEO-S017 décrivent méthodes d'essai, effets système et
équilibrage ; aucune certification du projet n'est revendiquée. Les lois de
similitude restent conditionnelles à même géométrie, densité et régime
d'écoulement. Le rapport 1,8 / 1,6 ne démontre pas un gain moteur réel.

La validation physique dépend de l'identité et de la métrologie du spécimen,
des interfaces choisies, du système moteur et du matériau/process documentés.
Les recherches sont disponibles et contrôlées ; ces conditions restent ouvertes.
