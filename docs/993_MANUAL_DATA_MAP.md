# Cartographie technique du manuel 993

Ce document relie les données structurées du projet Porsche Fanatics au
catalogue de rétroconception. Nous n'avons ni véhicule ni pièce donneuse. Les
nombres ci-dessous sont donc des spécifications publiées dans le manuel
d'atelier, pas des mesures prises par ce projet et pas des cotes de CAO.

## Accès et provenance

- [Index des procédures 993](https://porschefanatics.com/993/manual/) : 235
  entrées de numéro de réparation et de page.
- [Données techniques](https://porschefanatics.com/993/technical-data/) : 111
  valeurs extraites des fiches techniques.
- [Couples de serrage](https://porschefanatics.com/993/torques/) : 195 lignes
  réparties dans les tableaux par groupe de réparation.
- Source de référence du catalogue : `SRC-PORSCHE-WORKSHOP-MANUAL-993`.
- Pont vers l'index public et ses extractions :
  `SRC-PORSCHEFANATICS-993-MANUAL-DATA`.
- [Registre exhaustif des valeurs quantitatives](../catalog/manual/993-workshop-manual-measurements.json) :
  2 496 enregistrements, dont 2 190 occurrences issues des procédures OCR.

Le fichier PDF consulté localement n'est pas ajouté au dépôt. Le projet
Porsche Fanatics conserve ses extractions pour permettre la recherche et la
traçabilité, mais elles ne remplacent pas l'exemplaire autorisé du manuel. Les
pages publiques précisent également que les procédures, avertissements et vues
éclatées doivent être lus dans le manuel.

## Où chercher une information de pièce

| Famille | Zone du manuel | Utilité pour le catalogue |
|---|---|---|
| Moteur et distribution | groupes 10–15, notamment p. 15, 98, 108, 121, 137, 152–157, 177 | spécifications, jeux, limites d'usure et méthodes de contrôle |
| Boîte manuelle | groupe 3, p. 253–258 | variantes G50, rapports, capacités et couples de montage |
| Boîte Carrera 4 | groupe 3, p. 354 et suivantes | identification G64 et procédure propre à la transmission intégrale |
| Châssis et direction | groupes 4–5 | procédures et couples ; aucune géométrie de fabrication seule |
| Freinage | groupe 46, p. 725–728 | données de variante et limites d'entretien ; jamais une autorisation de fabriquer |
| Carrosserie et intérieur | groupes 51–68 | identification, dépose et montage ; généralement pas de plans cotés |
| Chauffage et climatisation | groupe 87 | procédures et repérage des sous-ensembles |
| Électricité | groupes 90–97 | repérage et procédures, sans extrapoler la géométrie des connecteurs |

## Valeurs utiles déjà contrôlées dans le PDF

### Véhicule et groupe motopropulseur — Carrera 993

Page PDF 15, fiche « Technical data » :

| Élément | Valeur imprimée | Variante / remarque |
|---|---:|---|
| Cylindres | 6 | Carrera 993 |
| Alésage | 100 mm | M64/05 manuel et M64/06 Tiptronic |
| Course | 76,4 mm | même fiche |
| Cylindrée réelle | 3 600 cm³ | même fiche |
| Rapport volumétrique | 11,3:1 | même fiche |
| Puissance EEC | 200 kW / 272 HP à 6 100 tr/min | déclaration de fiche, pas mesure du projet |
| Couple EEC | 330 Nm à 5 000 tr/min | déclaration de fiche |
| Masse boîte manuelle | 232 kg | boîte sèche, prête à monter, selon l'intitulé de la fiche |
| Masse Tiptronic | 224 kg | même contexte |

Page PDF 19, dimensions au poids DIN :

| Élément | ROW | USA |
|---|---:|---:|
| Longueur | 4 245 mm | 4 260 mm |
| Largeur | 1 735 mm | 1 735 mm |
| Hauteur | 1 300 mm | 1 315 mm |
| Empattement | 2 272 mm | 2 272 mm |
| Voie avant | 1 405 mm | 1 405 mm |
| Voie arrière | 1 444 mm | 1 444 mm |
| Garde au sol | 110 mm | 120 mm |
| Châssis sport — hauteur | 1 285 mm | à confirmer par variante |
| Masse à vide DIN | 1 370 kg | — |
| Masse 70/156/EEC | 1 445 kg | — |
| Masse maximale autorisée | 1 710 kg | 1 690 kg |
| Charge maximale avant / arrière | 720 / 1 065 kg | tableau Carrera |

La longueur, la hauteur, la garde au sol et la masse maximale ne doivent donc
pas être fusionnées dans une fiche générique « 993 ».

### Moteur interne et pièces d'usure

Ces valeurs sont des limites de contrôle du manuel. Elles sont utiles pour
définir une future campagne de métrologie ou vérifier un modèle, mais elles ne
définissent pas à elles seules une pièce imprimable.

| Sujet | Valeur | Page PDF |
|---|---|---:|
| Vilebrequin, diamètre palier principal d1 standard | 59,971–59,990 mm | 98 |
| Vilebrequin, diamètre tête de bielle d2 standard | 54,971–54,990 mm | 98 |
| Vilebrequin, diamètre de palier principal d3 standard | 30,980–30,993 mm | 98 |
| Réparation d1 / d2 / d3 | −0,25 ou −0,50 mm selon la colonne | 98 |
| Bride de vilebrequin d4 | 89,780–90,000 mm | 98 |
| Usure bride de vilebrequin | 89,580 mm | 98 |
| Ajustement pignon de distribution d5 | 42,002–42,013 mm | 98 |
| Diamètre d'appui d6 / limite d'usure | 29,960–29,993 / 29,670 mm | 98 |
| Logement de palier carter 1–8, standard | 65,000–65,019 mm | 98 |
| Logement de palier carter 1–8, surdimensionné | 65,250–65,269 mm | 98 |
| Jeu circonférentiel arbre intermédiaire, neuf | 0,035–0,084 mm | 137 |
| Limite d'usure du jeu circonférentiel | 0,10 mm | 137 |
| Jeu de montage cylindre-piston | 0,02–0,03 mm | 108 |

Groupes de tolérance piston/cylindre, page 108 :

| Groupe | Cylindre Ø | Piston Ø |
|---:|---:|---:|
| 0 | 100,000–100,007 mm | 99,970–99,980 mm |
| 1 | 100,007–100,014 mm | 99,977–99,987 mm |
| 2 | 100,014–100,021 mm | 99,984–99,994 mm |
| 3 | 100,021–100,028 mm | 99,991–100,001 mm |

Guides et soupapes :

| Sujet | Valeur | Page PDF |
|---|---|---:|
| Alésage intérieur du guide après usinage | 8,00–8,015 mm | 153 |
| Interférence de montage du guide | 0,06–0,08 mm | 153 |
| Guide standard, diamètre extérieur indiqué | 13,060 mm | 154 |
| Guide première cote réparation, diamètre extérieur indiqué | 13,260 mm | 154 |
| Jeu de basculement admissible du guide, admission/échappement | 0,80 / 0,80 mm | 152 |
| Soupape admission, tête a | 49 ± 0,1 mm | 155 |
| Soupape admission, queue b | 7,970 − 0,012 mm | 155 |
| Soupape admission, longueur c | 110,1 ± 0,1 mm | 155 |
| Soupape échappement, tête a | 42,5 ± 0,1 mm | 155 |
| Soupape échappement, queues b1 / b2 | 7,950 − 0,012 / 7,970 − 0,012 mm | 155 |
| Soupape échappement, longueur c | 109 ± 0,1 mm | 155 |
| Angle de portée admission / échappement | 45° / 45° | 155 |
| Longueur montée ressort admission M64/05–08 | 36,7 + 0,3 mm | 157 |
| Longueur montée ressort échappement M64/05–08 | 35,7 + 0,3 mm | 157 |
| Longueur montée ressort admission M64/20 RS | 37,2 + 0,3 mm | 157 |
| Longueur montée ressort échappement M64/20 RS | 35,8 + 0,3 mm | 157 |

Pour les soupapes RS, la même page donne entre parenthèses les têtes 51,5 mm
(admission) et 43,5 mm (échappement), ainsi que les variantes de diamètre de
queue. Il faut conserver la variante RS au lieu de remplacer la valeur Carrera.

### Distribution et courroie d'alternateur/ventilateur

Page PDF 177 : la distance entre la face de l'arbre intermédiaire et le pignon
arrière est 98,07 mm pour les cylindres 1–3 ; celle vers le pignon avant est
43,27 mm pour les cylindres 4–6. L'écart admissible de position des pignons
d'arbres à cames est ±0,25 mm. L'exemple imprimé avec A = 35,5 mm donne
133,57 ± 0,25 mm et 78,77 ± 0,25 mm.

Page PDF 121 :

- courroie usagée : 15–23 graduations à froid, 20–28 à température de service ;
- courroie neuve : 23–35 graduations à froid, puis 28–40 après environ 15 minutes
  au ralenti ou 10 miles d'essai ;
- outil indiqué : Porsche 9574 ; cales 0,5 et 0,7 mm, cette dernière étant
  repérée par un trou de 2 mm.

Ces graduations sont propres à l'instrument et ne sont pas des millimètres.

### Boîte manuelle et couples associés

Les pages 253–257 identifient les familles G50/20 et G50/21 pour la Carrera et
G50/31, G50/32 et G50/33 pour la Carrera RS. Les rapports finaux imprimés sont
3,444 pour les deux tableaux ; la fiche publique Porsche Fanatics expose le
détail des rapports par famille.

Page PDF 258, exemples à vérifier contre le groupe de réparation et la boîte
réelle avant intervention : bouchons d'huile M22×1,5 à 30 Nm, écrous M8 à 23 Nm,
plaque de serrage M6 à 10 Nm, contacteur de feu de recul M18×1,5 à 35 Nm et
mise à l'air M14×1,5 à 35 Nm. La table complète, qui comprend aussi les écrous
d'arbres, reste dans l'index public plutôt que d'être recopiée ici.

### Freinage : données conservées, fabrication bloquée

Les pages 725–726 décrivent la Carrera 4 ; les pages 727–728, la Carrera 4S
(Turbo-Look). Exemples imprimés :

| Variante | Disques avant/arrière | Épaisseur neuve avant/arrière | Limite d'usure avant/arrière |
|---|---|---|---|
| Carrera 4 | 304 / 299 mm | 32 / 24 mm | 30,0 / 22,0 mm |
| Carrera 4S Turbo-Look | 322 / 322 mm | 32 / 28 mm | 30,0 / 26,0 mm |

La Carrera 4 porte aussi les diamètres de pistons d'étrier 2×44 + 2×36 mm à
l'avant et 2×30 + 2×28 mm à l'arrière ; la Carrera 4S reprend ces diamètres
dans la fiche contrôlée. Les limites de faux-rond imprimées sont 0,05 mm pour
le disque, 0,04 mm pour le moyeu et 0,09 mm disque monté.

Ce sont des données d'entretien d'un organe de sécurité. Elles ne servent pas
à concevoir un étrier, un disque, une cale, un support de roue ou une pièce de
freinage dans ce projet. Toute future pièce de cette zone exige revue
professionnelle, calculs, essais et validation réglementaire documentée.

## Ce que ces données permettent maintenant

1. Identifier les familles et les variantes avant de demander une CAO ou une
   pièce donneuse.
2. Définir des plans de mesure : par exemple piston/cylindre, guide de soupape,
   pignon de distribution et éléments de console.
3. Contrôler un futur scan ou une pièce acquise contre des valeurs publiées,
   sans déclarer l'interface « ajustée » avant une mesure directe.
4. Prioriser les pièces intérieures non critiques, notamment la patte de
   console 964/993 recensée par `SRC-PRINTABLES-964-993-CONSOLE-SWITCH-TAB`.

Le registre `catalog/measurements/MEAS-MANUAL-993-ALL.json` contient désormais
les 2 496 spécifications documentaires indexées. Il ne s'agit pas de mesures
physiques du projet : aucune pièce, aucun véhicule et aucun instrument n'ont été
utilisés. Les séances instrumentées des pièces resteront séparées et pourront
être ajoutées lorsque les lectures brutes seront disponibles.
