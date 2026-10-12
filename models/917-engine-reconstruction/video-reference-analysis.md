# Analyse visuelle de la référence 917/30

Analyse du 12 octobre 2026, fondée sur les images effectivement extraites de
la [vidéo fournie](https://www.youtube.com/watch?v=NI_jfBTtziQ).
Comparaison avec le [rendu PicoGK actuel](mechanical-detail/engine-surfaces.png).
L'écart principal concerne l'architecture extérieure : enveloppes latérales
morcelées, conduits trop dégagés au-dessus du moteur et accessoires encore
insuffisamment intégrés. Ajouter des nervures décoratives ne résoudrait pas cet
écart.

## Source et méthode

- Auteur indiqué par YouTube : Racetrack Retreats ; publication indiquée :
  9 mai 2023 ; identifiant : `NI_jfBTtziQ`.
- Le titre présente un moteur de Porsche 917/30 de 1973 et annonce 1580 HP.
  Ces indications appartiennent à l'auteur ; la puissance n'est pas une
  charge de calcul vérifiée et la variante n'est pas identifiée par les pixels.
- Copie de consultation : 640 × 360 pixels, 30 images/s, 241,433333 s.
  Les métadonnées YouTube annoncent une résolution maximale supérieure,
  mais l'analyse porte sur la copie effectivement téléchargée.
- SHA-256 de cette copie :
  `8686cfdb8ea1a825dfaa43d622f41df22f45cd8c669dae32c9d02e91a32d593a`.
- Deux planches de repérage ont été examinées, puis neuf images extraites
  séparément à 40, 60, 70, 90, 100, 130, 135, 145 et 150 secondes. Les images
  ponctuelles servent aux repères ci-dessous ; les planches ne servent pas à
  attribuer une seconde exacte.
- Extraction reproductible :
  `ffmpeg -ss 40 -i video.mp4 -frames:v 1 frame-040.png`, en changeant la seconde.
  La vidéo et les images de consultation sont conservées dans `/tmp/`, hors Git.
- Les sous-titres automatiques n'ont pas pu être récupérés (HTTP 429).
  Aucune identification ci-dessous ne repose sur une transcription supposée.
- Les vues du moteur sur support et celles du moteur dans le châssis sont
  traitées séparément. Leur équivalence d'équipement n'est pas établie.
- Licence de reproduction des images et droit d'en dériver des surfaces :
  inconnus. Ce document publie les observations et les liens, sans images,
  vidéo, plaques ou identifiants du véhicule.

## Observations et conséquences pour notre modèle

| Image | Observation visible | Conséquence de conception ; limite |
|---|---|---|
| [00:40](https://www.youtube.com/watch?v=NI_jfBTtziQ&t=40s), moteur sur support | Deux enveloppes longues et arrondies encadrent une rangée de fils et de passages latéraux. Vis périphériques, bourrelets et ligne de joint sont visibles. | Les six capots presque cubiques par banc de notre rendu ne reproduisent pas cette silhouette. Étudier un habillage longitudinal pour les culasses 4V, avec réserves du mécanisme et accès aux fixations. Le nombre de pièces, les joints et les axes internes restent à mesurer. |
| [01:00](https://www.youtube.com/watch?v=NI_jfBTtziQ&t=60s) et [02:15](https://www.youtube.com/watch?v=NI_jfBTtziQ&t=135s), moteur sur support | Bloc à raccords métalliques répétés, conduites noires individuelles, couvercle boulonné, bouchon rouge, tringles et leviers. | Le montage évoque un ensemble de dosage/injection mécanique ; son identité et son fonctionnement ne sont pas prouvés par l'image. Il montre surtout le manque de raccords, de commande et d'accès maintenance de nos accessoires. Il ne justifie pas de remplacer notre architecture de commande ni de concevoir un circuit de carburant fonctionnel. |
| [01:10](https://www.youtube.com/watch?v=NI_jfBTtziQ&t=70s), moteur sur support | Corps cylindrique adjacent à des poulies et à une courroie ; petits carters à bossages, platines boulonnées, conduites et collecteurs proches du corps moteur. | Regrouper les accessoires autour d'interfaces plausibles mais explicitement candidates ; montrer brides, portées et vis. L'identité de chaque accessoire et son entraînement doivent être confirmés séparément. Notre grande plaque de distribution reste une solution candidate, sans fidélité historique établie. |
| [01:30](https://www.youtube.com/watch?v=NI_jfBTtziQ&t=90s) et [02:10](https://www.youtube.com/watch?v=NI_jfBTtziQ&t=130s), moteur installé | Deux longs volumes gris, un de chaque côté de la zone centrale ; tubes bleus longitudinaux, manchons orange à colliers, tringlerie transversale, faisceaux et enveloppe centrale dorée. Le châssis entoure étroitement ces volumes. | Rapprocher les trajets de suralimentation des bancs et traiter séparément tubes, manchons, colliers et supports. Vérifier ensuite les dégagements avec un châssis mesuré. Le rôle précis de tous les volumes et l'intérieur de l'enveloppe centrale ne sont pas visibles. |
| [01:40](https://www.youtube.com/watch?v=NI_jfBTtziQ&t=100s), moteur installé | Gros carter arrondi en forme de volute, coude court, plusieurs manchons orange et colliers ; volume noir courbe voisin et tubes de châssis devant le montage. | Le montage est compatible visuellement avec une partie du système de suralimentation. Garder nos turbos paramétriques et remplacer les raccordements génériques par des interfaces mesurées. L'image ne donne ni carte compresseur, ni jeu de rotor, ni identification certaine du volume noir, ni second turbo entier dans cette vue. |
| [02:25](https://www.youtube.com/watch?v=NI_jfBTtziQ&t=145s) et [02:30](https://www.youtube.com/watch?v=NI_jfBTtziQ&t=150s), moteur installé | Corps métalliques nervurés, raccords coudés, flexibles, tuyaux et pattes, partiellement masqués par la structure. Un grand embout ouvert est visible à 150 s. | Ajouter les chemins de service et les fixations après identification des organes. Ne pas attribuer ces nervures aux cylindres ni le carter à une fonction particulière : la proximité de la transmission et les masques rendent cette identification incertaine. Le grand embout ne suffit pas à reconstituer tout l'échappement. |

## Ce qui explique l'aspect simplifié actuel

1. **Silhouette des bancs.** La répétition de six boîtes indépendantes attire
   davantage le regard que les culasses et les carters. Les rayons ajoutés aux
   capots actuels ne créent pas l'enveloppe longitudinale visible à 40 s.
2. **Implantation des conduits.** Les grandes boucles isolées au-dessus du modèle
   amplifient sa hauteur. La référence installée montre des conduits contenus
   par les bancs et le châssis. Abaisser uniquement une boucle sans contrôler
   les interfaces et les dégagements ne suffit pas.
3. **Jonctions mécaniques.** La référence contient de nombreux raccords, colliers,
   portées, bossages, lignes de joint et dispositifs de commande. Un tube continu
   et un accessoire bien fermé ne représentent pas ces assemblages démontables.
4. **Présentation et architecture.** Les surfaces opaques et le détail des
   maillages améliorent la lecture, mais ne corrigent ni les proportions de
   conception, ni l'intégration des organes. Les différences observées demandent
   des changements de géométrie et d'implantation.

## Suite PicoGK prioritaire

Les culasses 4V et les turbos existants restent la base de notre moteur hybride.
Cette vidéo ne transforme pas leur conception en reproduction du moteur filmé.

| Priorité | Modification à étudier | Contrôle nécessaire avant acceptation |
|---|---|---|
| 1 | Enveloppes longitudinales arrondies des bancs, avec volumes creux et accès démontables | Interfaces de culasses conservées ; dégagement des soupapes, cames et distribution ; fermeture des surfaces et accès aux vis ; plan de joint à qualifier |
| 2 | Trajets plus compacts autour des sorties des turbos et des échangeurs | Ports et poses conservés ; passages ouverts ; intersections avec les autres pièces ; rayons et dépoudrage ; pertes de charge et interfaces d'étanchéité encore à calculer/mesurer |
| 3 | Accessoires intégrés : bossages, platines, supports, raccords et commandes | Organes identifiés, ancrages et chemin des efforts documentés ; retrait et maintenance possibles ; aucune vis purement décorative acceptée comme preuve d'attachement |
| 4 | Supports et transitions internes bioniques via les fonctions PicoGK existantes | Zones de fixation et zones interdites conservées ; témoin dense comparable ; résistance, rigidité, fatigue et procédé à qualifier |

La bionique convient aux supports et aux transitions de canaux, à partir
d'ancrages et de charges connus. Aucune structure ramifiée extérieure n'est
identifiable dans ces images. Répartir des branches sur tous les carters serait
un choix de conception neuf, sans justification issue de cette référence.

## Informations que ces images ne fournissent pas

Aucune échelle calibrée, orthovue ou caméra étalonnée n'est disponible. Les
diamètres, entraxes, épaisseurs et volumes ne sont donc pas mesurés ici.
Une cote extraite d'un autre dossier FIA ou du scan doit conserver sa propre
variante et sa provenance, sans être attribuée à cette vidéo.

Les couleurs dorées, grises, bleues et noires ne déterminent pas les alliages,
les traitements, les revêtements ou le procédé de fabrication. Les intérieurs
des culasses, les quatre soupapes demandées, les chambres, les jeux, le
vilebrequin, les passages d'huile/eau et les interfaces cachées ne sont pas
validés par ces vues. Les pressions, températures, efforts, performances
thermiques, fatigue et aptitude à l'impression métallique restent inconnus.

Cette analyse apporte une référence de silhouette et d'intégration. Elle ne
qualifie aucune pièce comme fonctionnelle ou prête à fabriquer. Elle ne modifie
pas les sources ni les reçus d'exécution de l'étape mécanique déjà publiée.
