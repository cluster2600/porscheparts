# Vue d’ensemble de la chaîne

[Schéma vectoriel](process.svg), [image PNG](process.png), [PDF](process.pdf).

Le dessin décrit les six étapes et les trois entrées du
[processus](../../manufacturing/PART_WORKFLOW.md). Les numéros se suivent de
gauche à droite sur la première rangée, puis de droite à gauche sur la seconde.
Il présente les actions et les fichiers attendus, sans attribuer un résultat
à une étape qui n’a pas encore terminé.

La masse affichée, arrondie à trois décimales, provient de l’
[export de la géométrie retenue](../../../parts/993-eng-carrier-0001/derived/workflow-20261016/export.json) :
1,262212620786407 kg pour le STEP
`de0e55a3150dacc5428bbc301d18d2e43477f038c3f4df295d9373af8e906b63`.
Le plafond est celui demandé par Maxime : 1,30 kg.

Le fichier SVG est autonome, sans script, police téléchargée ni image externe.
Son texte reste sélectionnable et sa mise à l’échelle conserve les traits et
les caractères. Il a été inspecté en entier dans le navigateur, à la largeur
de la fenêtre, après vérification de ses six cartes et de leurs flèches.

Les exports emploient le logiciel déjà installé `rsvg-convert 2.63.2` :

```sh
rsvg-convert --width 1500 --keep-aspect-ratio --output process.png process.svg
rsvg-convert --format pdf --width 1500 --keep-aspect-ratio --output process.pdf process.svg
```

Le [reçu des exports](exports.json) lie les trois fichiers et la source de
masse. L’unique page du PDF a aussi été rendue puis inspectée en entier.
