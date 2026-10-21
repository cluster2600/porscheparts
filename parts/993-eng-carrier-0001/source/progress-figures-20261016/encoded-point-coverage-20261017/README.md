# Points encodés déjà couverts — peau 13 de la zone 000

Cette planche utilise le diagnostic réellement exécuté sur le maillage original
`c351989c…` : **985 faces, 1 034 hauteurs, 703 événements ponctuels**, tous
couverts par un vecteur encodé non nul du même groupe, dans le même NPZ et à
la même hauteur. Le diagnostic conserve les 460 440 coupes rationnelles avant
encodage ; 459 737 primitives ont un encodage non nul. Il ne change aucun sommet
ni aucune face du support.

- [PNG](render/carrier-703-points-couverts.png),
  [SVG](render/carrier-703-points-couverts.svg),
  [PDF](render/carrier-703-points-couverts.pdf).
- [Diagnostic exécuté](data/assessment.json),
  [preuves des 1 034 hauteurs](data/layers.jsonl),
  [reçu d'exécution](data/execution-receipt.json),
  [revue root](data/root-terminal-review.json).
- [Sources et empreintes](inputs.json),
  [reçu du rendu](render/render-receipt.json).

La partie A compte les événements par face et par hauteur. La partie B montre
la couche 118, à Z = 7,11 mm : les deux extrémités distinctes de la coupe exacte
de la face 170703 s'arrondissent au même point P. Ce point appartient exactement
à la trajectoire encodée non nulle de la face 170699. La coupe exacte reste
conservée ; seule la primitive machine P → P peut être omise dans la nouvelle
règle proposée. La trajectoire verte est limitée à son extrait dans la cellule
d'arrondi montrée. Chaque axe est normalisé par sa propre ULP, indiquée dans
le reçu ; ce zoom ne représente pas une dimension de fabrication.

Le calcul stdlib a terminé avec un code réel 0 en 74,845 s ; le superviseur
a collecté l'enfant et constaté le groupe fermé en 75,126 s. Les douze fichiers
liés sont inchangés. Root a relancé les quinze petits tests avant le calcul,
puis relu les 1 034 lignes et leurs 703 témoins après collecte.

Le périmètre reste **la peau 13**. Les 17 384 événements du maillage complet,
les contacts, les deux graphes d'exposition et l'intégration du découpeur ont
leurs contrôles suivants. Cette image ne donne aucune admission de la zone 000
ni des sept zones. Les anciens refus du découpeur strict restent conservés.

Le rendu utilise Matplotlib et les données copiées ici. Depuis n'importe quel
répertoire, avec le Python de dessin installé dans le projet :

```sh
python3 -B CHEMIN/encoded-point-coverage-20261017/render.py NOUVELLE_SORTIE
```

La sortie doit être neuve. Le script vérifie les empreintes, les 1 034 hauteurs,
le total des événements et l'appartenance rationnelle de chaque point à son
témoin non nul avant de tracer. Le PNG publié a été inspecté visuellement.
