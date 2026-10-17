# Images du travail en cours — 16 octobre 2026

Ouvrir `index.html` pour parcourir les planches de ce dossier hors ligne. Les fichiers
PNG restent disponibles individuellement à leur définition complète.

La navigation donne aussi accès aux cartes mécaniques déjà calculées :
[appuis rigides](mechanics.html), [appuis souples](mechanics-springs.html),
et aux [surfaces corrigées de la région droite](right-supports.html).
Chaque planche conserve son propre reçu et son périmètre de calcul.

La [planche locale de la peau gauche](chart002-local-20261016/README.md)
complète ces cinq vues. Elle conserve ses trois JSON réels, son script de
rendu et son reçu propres ; elle ne modifie pas les preuves historiques des
cinq planches initiales.

Les [deux planches des sept enveloppes natives](sealed-envelopes-20261016/README.md)
ajoutent les volumes de construction dans la pose réelle et les agrandissements
des petites régions 003/009. Leurs propres reçus conservent les sept maillages,
les sources du rendu et les contrôles des barres d’échelle. Le rejeu depuis
une copie séparée reproduit les deux PNG à l’octet. Ces volumes précèdent les
grilles et les couches des supports, encore en cours de calcul.

Les [deux planches des surfaces de supports calculées](calculated-surfaces-20261017/README.md)
montrent les régions 003/009/010 dans la pose conservée, puis leurs grilles,
peaux et dents en détail. Les trois checkpoints sont revérifiés localement ;
le contrôle des sept régions et des couches reste en cours. Un rejeu depuis
une copie séparée et un autre répertoire courant reproduit les deux PNG
à l’octet. Les PDF, SVG, sources et reçus accompagnent ces images.

Les deux nouvelles vues utilisent le STL retenu et les triangles des supports
de l'essai `real-support-source-008-015`. Les cotes, le comparatif du maillage
et la couche 518 sont des copies identiques des figures calculées auparavant.
Le [reçu](figures.json) conserve leurs empreintes et celles des entrées.

La pièce pèse 1,262212621 kg pour une limite de 1,30 kg. L'essai de supports
perforés montré est refusé : 26 composantes, soit 35,66 mm² de surfaces,
n'ont pas les deux ancrages requis. Il représente la région droite seule,
pas une préparation complète admise. La vue du détail projette les triangles
dans leur plan réel ; aucune surface supplémentaire ne comble les écarts.

Régénération depuis la racine du dépôt, avec le runtime PySLM reproduit :

```sh
work/part-workflow/runtimes/pyslm-coverage-reproduced-012/env/bin/python \
  scripts/render_carrier_progress.py \
  work/part-workflow/run-001 \
  work/carrier-process-20261016/real-support-source-008-015 \
  work/part-workflow/progress-images-new
```

Le répertoire de sortie doit être neuf. Le rendu refuse les divergences
d'identité entre STEP, masse, audit CAD/maillage et STL, ainsi qu'entre le
graphe d'ancrage et les triangles qu'il colore. VisPy utilise un tampon de
profondeur pour les vues 3D ; Matplotlib trace le détail dans le plan réel.

Les cinq images ont été relues visuellement ; les empreintes des copies et
le test ciblé de coloration du graphe passent. Les cadrages intermédiaires
sont conservés dans `work/part-workflow/progress-images-001` à `003` avec
leur motif de refus éditorial.

La [planche de la grande zone 000](region000-material-20261017/README.md)
montre ses 171 694 triangles originaux : 322 grilles et 15 peaux, avec un graphe
matériel connecté. Elle conserve le refus du découpeur strict et indique la
correction de triangulation en cours. Les sources, tableaux, index des groupes
et exports PNG/SVG/PDF sont inclus ; le rendu a été exécuté depuis une copie séparée.

La [planche locale du chart 152 de la région 008](chart008-local-20261017/README.md)
montre deux bandes déjà contenues dans le domaine source, avec leurs dimensions
et les reçus exacts conservés. Les contacts du composant restent non validés ;
aucune admission régionale ou globale n’est déduite de cette image. La
[revue de publication](chart008-local-20261017/publication-validation.json)
lie les copies exactes à l’inspection du PNG et du PDF par root.

La [planche des points encodés déjà couverts](encoded-point-coverage-20261017/README.md)
explique le diagnostic complet de la peau 13 de la zone 000 : 703 événements
contrôlés sur les 1 034 hauteurs, avec les coupes rationnelles conservées et
un témoin non nul du même groupe pour chaque point encodé. Les données, les
preuves et les exports PNG/SVG/PDF sont inclus. Les autres groupes et les
graphes d'exposition restent à contrôler avec cette nouvelle règle.
Le [rejeu depuis une copie séparée](encoded-point-coverage-20261017/replay-validation.json),
lancé depuis `/tmp`, reproduit les trois exports à l'octet.
Le [contrôle suivant des 17 384 événements](../process-point-encoding-20261017/README.md)
termine également les 1 034 hauteurs avec tous les témoins requis ; cette
capsule conserve le helper, les tests et les preuves complètes. La planche
reste liée à son diagnostic historique de la seule peau 13.

La [planche d'encombrement de la pose actuelle](machine-envelope-20261017/README.md)
projette les 587 404 triangles réels en XY et XZ. Elle montre la plaque de
500 mm, une chambre nominale de 650 mm, les marges et les deux conventions de
hauteur des machines documentées. Les sources constructeur sont liées dans
le dossier. Un [rejeu depuis la copie publiée](machine-envelope-20261017/publication-validation.json),
lancé depuis `/tmp`, reproduit les PNG/SVG/PDF à l'octet.

La [planche du retrait imposé et du débridage](wholepart-release-20261017/README.md)
montre les quatre champs natifs en double précision sur la pièce entière.
Le cas uniforme passe le seuil initial de déformation de 10⁻⁷. Sous le champ
quadratique imposé et le bridage provisoire, le déplacement maximal après
libération vaut 58,090 µm ; l'amplification visuelle de 500 est indiquée.
Les 103 534 nœuds et les quatre champs sont conservés dans les données locales.
Le [rejeu par root depuis une copie séparée](wholepart-release-20261017/publication-validation.json)
reproduit les trois formats à l'octet. Cette sensibilité mécanique reste
distincte du calcul thermique du procédé d'impression.
La [capsule du cas natif complet](../design-20261016/wholepart-native64-20261017/README.md)
fournit également les entrées comprimées, les quatre états et les commandes
de restauration et de réanalyse, sans nouvelle exécution du solveur.

La [planche des contacts de la région 000](region000-contacts-20261017/README.md)
montre la première coupe réelle des 337 groupes de supports, puis un détail
aux mêmes coordonnées. Elle conserve tous les intervalles de contact avant
et après encodage des segments. Trois contacts devenus points ne créent aucune
ancre supplémentaire. Les 129 023 certificats ont été revérifiés séparément
avec des fractions exactes ; la portée reste une couche et une région.
Les [trois formats rejoués depuis la copie publiée](region000-contacts-20261017/publication-validation.json)
accompagnent les données compactes et le script de rendu autonome.
