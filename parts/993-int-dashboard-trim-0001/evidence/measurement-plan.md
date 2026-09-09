# Plan de mesure — 993-INT-DASHBOARD-TRIM-0001

Catégorie phase 2 : surface libre de grande dimension, photogrammétrie ou scan,
recalée sur des cotes mesurées séparément.

## Porte d'entrée : la voiture est-elle sans airbag passager ?

**Cette vérification précède tout le reste, et elle peut arrêter le projet.**

| code d'option | équipement | suite |
|---|---|---|
| `M564` | sans airbag | mesure autorisée |
| `M002` / `M003` | Carrera RS et Clubsport, illustration « for cars without Airbag » | mesure autorisée |
| `M561` | airbag conducteur seul | vérifier côté passager, puis décider |
| `M562` | airbag conducteur **et passager** | **arrêt** |

Le code se lit sur l'étiquette d'options du véhicule, sans relever le numéro de
châssis ni aucune donnée personnelle. Photographier l'étiquette, en masquant le
numéro de châssis, et joindre la photo à la fiche de mesure.

Contrôle croisé, à faire même si l'étiquette est claire : ouvrir le vide-poches
et regarder l'envers de l'habillage côté passager. Un volet de déploiement se
voit — ligne de rupture moulée, module boulonné derrière. S'il y en a un, la
pièce sort du périmètre quelle que soit l'étiquette.

## Objet

- Pièce : habillage de planche de bord, côté conduite à gauche `993 552 055 00`
  ou `993 552 055 70` (RS M003) ; à droite `993 552 056 00` / `70`
- Variante et année : à confirmer sur le véhicule
- Pièce mesurée : **en place puis déposée**, les deux états sont exigés
- Responsable : contributeur
- Date :

## Instruments

| Instrument | Plage | Résolution | Étalonnage connu |
|---|---:|---:|---|
| Pied à coulisse | 0–150 mm | 0,01 mm | contrôle du zéro |
| Mètre ruban rigide ou règle | 0–1500 mm | 1 mm | comparé à la barre d'échelle |
| Appareil photo | | | focale fixe, mise au point verrouillée |
| Deux barres d'échelle certifiées | 100 et 500 mm | | valeurs certifiées à déclarer |
| Cibles codées | | | ≥ 40, réparties sur la pièce et autour |

Une seule barre d'échelle sur une pièce de 1,4 m laisse l'erreur d'échelle
croître aux extrémités. D'où deux barres, dont une longue, posées en travers.

## Repère

Origine au **centre de l'appui central sur la traverse de caisse**, X positif
vers la droite du véhicule, Z vers le haut, Y vers l'avant. La photogrammétrie
ne donne pas d'origine : c'est le recalage sur les interfaces mesurées qui la
fixe.

Le repère du véhicule est celui du jumeau, pas celui de la pièce : les cotes
d'interface doivent pouvoir être rattachées au pied de pare-brise et aux
montants, qui appartiennent à la caisse.

## L'état de l'original se mesure avant de le croire

Un habillage de trente ans est fissuré, gauchi par le soleil, et **contraint par
ses fixations** : il peut se détendre en sortant de la voiture. Mouler cette
forme-là produirait une pièce fausse.

- Photographier chaque fissure, déformation, réparation ou trace de recollage,
  avec une réglette dans le champ.
- Relever `D01` à `D04` **en place**, puis les mêmes après dépose. Consigner les
  deux séries. Un écart supérieur à 2 mm signifie que la pièce s'est détendue et
  que la forme déposée n'est pas la forme de montage.
- Noter l'exposition du véhicule : garage, extérieur, pare-soleil.

## Dimensions critiques

Elles ne viennent pas du scan. Elles sont mesurées séparément et servent à
vérifier puis à mettre à l'échelle la reconstruction.

| ID | Description | En place | Déposé | Incert. mm | Méthode | Rép. |
|---|---|---:|---:|---:|---|---:|
| D01 | Longueur hors tout, montant à montant | | | | direct | 3 |
| D02 | Largeur au droit de la casquette d'instruments | | | | direct | 3 |
| D03 | Hauteur du plan d'appui au sommet de casquette | | | | direct | 3 |
| D04 | Flèche du bord avant, corde et hauteur | | | | direct | 3 |
| D05 | Entraxe des fixations, appui par appui | | | | direct | 3 |
| D06 | Diamètre des perçages d'écrou à griffes | | | | direct | 3 |
| D07 | Ouverture d'aérateur central, L x H | | | | direct | 3 |
| D08 | Ouvertures d'aérateurs latéraux, L x H | | | | direct | 3 |
| D09 | Ouverture de casquette d'instruments | | | | direct | 3 |
| D10 | Fentes de dégivrage, longueur et largeur | | | | direct | 3 |
| D11 | Points de fixation de la baguette de genoux | | | | direct | 3 |
| D12 | Jeu à la jonction de console centrale | | | | direct | 3 |
| D13 | Jeu au pied de pare-brise | | | | direct | 3 |
| D14 | Épaisseur de peau, en trois points hors nervure | | | | direct | 3 |

`D11` n'est pas une cote de style. La baguette de protection des genoux —
`964 552 053 00` / `993 552 054 00`, ou `964 552 077 70` / `964 552 078 70` sur
RS M003 — est une pièce séparée qui reste d'origine. Une reproduction qui
déplacerait ses points supprimerait une protection.

## Masse

Peser l'habillage déposé, nu, sans baguette ni aérateurs, avec une balance à
1 g près. Trois pesées. La table d'un préparateur annonce 2,1 kg ; c'est une
valeur de vendeur, et l'étape zéro est de la remplacer par une mesure.

## Photogrammétrie

- Surface sombre et grenée : c'est favorable, contrairement à un vernis
  brillant. Ne rien pulvériser sans avoir consigné l'état initial.
- Éclairage diffus, pas de flash direct : les reflets détruisent la corrélation.
- Deux tours complets, hauteurs d'appareil différentes, recouvrement ≥ 70 %.
- Couvrir l'envers : c'est lui qui porte les appuis, les nervures et les
  épaisseurs, donc la géométrie utile à un moule.
- Joindre un manifeste : appareil, focale, nombre de vues, logiciel, version,
  erreur de reprojection, barres d'échelle utilisées et écart résiduel.

## Livrables

- Photo de l'étiquette d'options, châssis masqué, et photo de l'envers côté
  passager établissant l'absence de volet d'airbag.
- Les deux séries `D01`–`D14`, en place et déposé, trois répétitions chacune.
- Trois pesées.
- Nuage de points ou maillage, avec son manifeste et son erreur d'échelle.
- Fiche JSON dans `catalog/measurements/`.

## Ce que ce plan ne fait pas

Il ne produit ni CAO, ni moule, ni pièce. Il produit de quoi décider si une
reproduction est possible **et** si la pièce d'origine mesurée est saine. Le
comportement en choc d'un stratifié rigide dans la zone de heurt des occupants
n'est pas traité ici : c'est une limite consignée dans la fiche de la pièce, et
elle reste ouverte.
