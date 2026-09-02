# F34 — culasse 917-inspired quatre soupapes refroidie par air

> **RETIRÉ COMME GÉOMÉTRIE PRODUIT.** Le volume rectangulaire F34 ne reproduit
> ni la silhouette, ni les bossages, ni le réseau réel d'ailettes du scan 935.
> Depuis F36, il ne peut servir que de régression de méthodes numériques. Ses
> CFD et EF ne constituent aucune preuve de performance pour la géométrie
> scan-conforme. Voir [la reconstruction F36](917_SCAN_CONFORMING_4V_F36.md).

## Résultat

F34 archive une CAO paramétrique défeaturée, un STEP de prototype de procédé,
une image de cette enveloppe et une campagne virtuelle traçable. Il ne livre
pas une géométrie de culasse crédible ni une culasse prête à
imprimer ou à démarrer. Les deux scans disponibles suffisent à amorcer une
géométrie et à identifier des interfaces, mais pas à prouver l'échelle absolue,
l'identité dimensionnelle Porsche 917, les volumes internes ni le comportement
du matériau imprimé à chaud.

![Culasse F34 4V refroidie par air](../twins/reference-917-engine/evidence/f34/product-aircooled-4v-f34.png)

Le statut machine est `virtual_campaign_executed_release_blocked`. Toutes les
portes de fabrication métallique, de démarrage moteur et de validation physique
restent à `false` dans le
[rapport consolidé](../twins/reference-917-engine/evidence/f34/report.json).

## Frontière imposée par les scans

| Source locale non publiée | Observation | Usage F34 | Interdiction |
| --- | ---: | --- | --- |
| carter/cylindres 917 | 2 465 879 triangles, 101 809 arêtes ouvertes, aucune culasse | axes, rangées de cylindres et contexte externe | aucune cote de culasse ni échelle absolue revendiquée |
| culasse 935 | 2 466 040 triangles, 99 876 arêtes ouvertes | morphologie à ailettes et graines d'interface | aucune identité ou compatibilité Porsche 917 revendiquée |

Les valeurs OBJ `113,52637`, `90,81249`, `86,74277 × 85,91584` et
`10,74024` sont plausibles en millimètres, mais l'unité n'est pas confirmée.
Les scans bruts restent locaux et ne sont ni copiés ni redistribués. Le contrat
[aircooled-4v-scan-f34.json](../twins/reference-917-engine/aircooled-4v-scan-f34.json)
porte leurs SHA-256 et les limites d'usage.

## Architecture construite

La source maître est
[`build_aircooled_4v_head_f34.py`](../twins/reference-917-engine/source/build_aircooled_4v_head_f34.py).
Elle produit un unique solide B-Rep et sépare la peau fonctionnelle de
l'enveloppe étanche destinée au calcul d'air externe.

| Paramètre | Valeur nominale F34 |
| --- | ---: |
| Soupapes | 2 admission Ø 32 mm + 2 échappement Ø 27 mm |
| Angle inclus | 36° |
| Levées maximales | 10,5 mm admission, 9,5 mm échappement |
| Ailettes | 18, pas 5,2 mm, épaisseur 2,2 mm |
| Surface totale CAO | 0,727242 m² |
| Surface de l'enveloppe de refroidissement | 0,670396 m² |
| Volume du solide | 2,660509 l |
| Encombrement | 200,0 × 208,4 × 114,1 mm |

Le
[STEP publié](../twins/reference-917-engine/evidence/f34/917-head-aircooled-4v-f34-process-prototype.step)
reste un **prototype de procédé**. Il manque notamment les interférences de
sièges et guides, les filetages, états de surface, tolérances, réseau complet
d'huile, porte-arbres complet, supports et compensation propres à la machine
LPBF.

## Matière, soupapes et ressorts

Le candidat virtuel retenu pour la culasse est **Constellium Aheadd HT1** après
traitement haute température. La fiche fournisseur utilisée indique un domaine
de service voisin de 260 °C, une limite d'élasticité de 216 MPa à 250 °C, une
résistance ultime de 265 MPa à 250 °C et 5 % d'allongement. La conductivité
`120 W/(m·K)` utilisée pour le screening n'est pas une carte fournisseur
qualifiée à chaud.

Ce choix reste conditionnel à des éprouvettes issues de la machine et du lot de
poudre retenus : orientation, HIP ou traitement, porosité, module, dilatation,
conductivité, fatigue, fluage et TMF. Sans ces cartes, Aheadd HT1 n'est pas une
matière libérée.

- admission : soupape forgée ou usinée Ti-6Al-4V candidate, non imprimée ;
- échappement : soupape achetée Inconel 751 candidate, non imprimée ;
- ressorts : double ressort acheté en fil CrSi ultra-propre, grenaillé et
  nitruré, `400 N` au siège, raideur combinée `105 N/mm`, non imprimé.

Le calcul cinématique à 9 000 tr/min conserve une marge de force positive, mais
il ne remplace ni calcul de contact came/poussoir, ni fatigue, ni contrôle de
surge sur spintron.

## Comment la chaleur est censée sortir

Le chemin prévu est : ponts de chambre et sièges → corps aluminium → pieds
d'ailettes → dix-huit ailettes → air forcé et caréné. Les soupapes d'échappement
évacuent aussi une partie de leur chaleur par le siège et le guide. Les retours
d'huile sont ouverts dans la CAO, mais aucun réseau d'huile complet ni jet
d'huile n'est validé.

F34 ne résout pas encore ce chemin complet. Le calcul 3D externe impose une
température de paroi de `533,15 K` et ne contient ni gaz de combustion, ni
conduction dans le métal, ni sièges/guides, ni huile : c'est une CFD de
convection, pas une CHT. Plus important, le domaine à `77 m/s` transporte
environ `8,3 kg/s`, contre `0,85 kg/s` par culasse au point burst du contrat.
Sans carénage et répartition d'air mesurés, la dissipation obtenue est une
sensibilité numérique et non le bilan thermique du moteur.

## Deux méthodes indépendantes pour le refroidissement externe

La comparaison emploie deux discrétisations réellement différentes : volumes
finis RANS avec OpenFOAM 14, puis Lattice Boltzmann avec FluidX3D. Changer
uniquement le solveur linéaire, PETSc ou AmgX n'aurait pas constitué une seconde
méthode physique.

| Résultat au même domaine externe | OpenFOAM FVM | FluidX3D LBM, maille la plus fine |
| --- | ---: | ---: |
| Cellules | 734 985 | 16 220 160 |
| Débit total | 8,290 kg/s | 8,277 kg/s |
| Chaleur de paroi | 18,158 kW | 20,753 kW |
| Coefficient effectif | 120,38 W/(m²·K) | 137,59 W/(m²·K) |
| Perte de pression | 1 859 Pa | 932 Pa |
| Convergence statistique/énergétique | oui, bilan total 1,03 % | oui |
| Indépendance de maillage | non démontrée, une maille | échec, écart fin 23,81 % sur la chaleur |

OpenFOAM passe `checkMesh` standard, mais le contrôle strict signale 25 611
cellules concaves et 6 faces à faible poids d'interpolation. La comparaison
finale échoue aussi : `12,50 %` d'écart sur le coefficient effectif pour une
limite de `12 %`, et `49,87 %` sur la perte de pression pour une limite de
`15 %`. Le fichier
[openfoam-external-cooling.json](../twins/reference-917-engine/evidence/f34/openfoam-external-cooling.json)
et l'
[étude FluidX3D](../twins/reference-917-engine/evidence/f34/fluidx3d-mesh-study.json)
conservent les valeurs complètes.

## Cycle, charge de pression et comparaison 2V/4V

Deux modèles 0D exécutés séparément ont été recoupés : réseau de réacteurs
Cantera 3.2.0 et modèle indépendant Wiebe-Annand.

| Sortie non corrélée | Cantera | Wiebe-Annand | Écart | Gate |
| --- | ---: | ---: | ---: | --- |
| Puissance mécanique | 1 601,20 hp | 1 644,89 hp | 2,66 % | passe le seuil numérique |
| Pression de pointe | 24,686 MPa | 18,798 MPa | 23,85 % | échec |

La pression Cantera, plus haute, est appliquée comme charge conservatrice au
screening EF. La cible de 1 600 hp n'est pas prouvée : aucun des deux modèles
n'est corrélé à une trace de pression cylindre ou à un banc.

La comparaison deux contre quatre soupapes disponible vient de F33 et utilise
des ports équivalents, pas la culasse F34 complète : sur la maille fine,
`0,113341 kg/s` en 2V contre `0,136519 kg/s` en 4V, soit `+20,45 %`. Le banc de
flux quasi stationnaire virtuel donnait `+15,28 %`. Ces deux tendances justifient
de poursuivre l'architecture 4V, mais elles ne constituent pas une validation
2V/4V scan-seeded avec soupapes mobiles.

## Calcul thermo-mécanique

CalculiX 2.21 applique `24,686 MPa`, un gradient prescrit de 260 à 120 °C et une
carte élastique hypothétique Aheadd HT1. Trois maillages ont été exécutés.

| Taille max | Tétraèdres | von Mises P95 | von Mises max | Déplacement max |
| ---: | ---: | ---: | ---: | ---: |
| 7 mm | 105 906 | 19,55 MPa | 217,60 MPa | 1,0508 mm |
| 5 mm | 204 661 | 17,40 MPa | 167,08 MPa | 1,0527 mm |
| 4 mm | 342 461 | 16,86 MPa | 262,04 MPa | 1,0533 mm |

Le déplacement et le P95 se stabilisent (`0,05 %` et `3,11 %`), mais le maximum
de contrainte varie de `36,24 %` entre les deux dernières mailles. Le maximum
fin dépasse les `216 MPa` à chaud, marge `0,824`. Une singularité locale est
possible, mais elle doit être résolue par rayons, contacts, maillage local et
carte non linéaire; elle ne peut pas être ignorée. Elmer, le second solveur EF
prévu au contrat, n'a pas été exécuté. Le
[rapport de maillage CalculiX](../twins/reference-917-engine/evidence/f34/calculix-mesh-study.json)
ferme donc la gate de résistance.

## Outils réellement exécutés et outils bloqués

| Outil | État F34 |
| --- | --- |
| OpenFOAM 14 | CFD externe exécutée 800 itérations, puis un pas diagnostic d'extraction énergétique |
| FluidX3D | trois grilles exécutées, convergence statistique oui, indépendance non |
| CalculiX 2.21 | trois maillages exécutés |
| Cantera 3.2.0 / Wiebe-Annand | deux calculs 0D exécutés et comparés |
| AATE/ICengines | compilé dans l'image CAE, cas mobile non exécuté faute de volumes internes étanches |
| Elmer | non exécuté |
| openHFDIB | évalué, non retenu : dernier commit observé 2020-07-11 et aucune qualification OpenFOAM 14/versionnée |
| PhysicsNeMo | 0 cas classiques convergés sur les 200 requis, entraînement interdit |
| Omniverse SimReady | prévol officiel bloqué, aucune conversion USD ni validation revendiquée |

Les images locales `linux/amd64` ont été construites et testées pour la chaîne
OpenFOAM/AATE/Gmsh/CalculiX et pour FluidX3D. L'
[audit d'exécution](../twins/reference-917-engine/evidence/f34/toolchain-audit.json)
distingue leurs identifiants locaux d'un digest GHCR. Kali et Vast n'ont pas été
utilisés; aucun coût GPU distant n'était nécessaire pour cette campagne bornée.

## Reproduction et contrôle

```bash
make 917-aircooled-4v-f34-cae-image
make 917-aircooled-4v-f34-fluidx3d-image
make 917-aircooled-4v-f34-publish
make 917-aircooled-4v-f34-check
make check
```

Le dossier
[`evidence/f34`](../twins/reference-917-engine/evidence/f34/README.md)
contient dix artefacts air-cooled suivis et hachés dans `publication.json`.
Les autres preuves F34 présentes dans ce répertoire conservent leur propre
manifeste. Les STL lourds,
les maillages, les champs solveurs et les scans restent hors Git; le script
paramétrique et le STEP compact sont publiés.

## Conditions minimales avant impression ou démarrage

Il faut au minimum confirmer l'échelle et les interfaces, reconstruire les
volumes internes, ajouter le carénage d'air réel, corriger les maillages,
effectuer les séquences FVM/LBM et CalculiX/Elmer aux débits de conception,
faire une CHT puis une fatigue/fluage/TMF avec cartes éprouvettes, définir le
procédé LPBF et les reprises, valider CT/CND, banc de flux, spintron et banc
moteur instrumenté, puis obtenir la revue et la signature d'un ingénieur
responsable. Tant que ces éléments manquent : **impression métallique interdite
et démarrage moteur interdit**.
