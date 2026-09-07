# Ouvre-porte intérieur 993 — concept métallique F0

Ce troisième pilote est un levier intérieur d'ouverture de porte. Le catalogue
PorscheFanatics identifie les références gauche et droite `993 555 851 00` et
`993 555 852 00` dans les illustrations PET `807-10` et `807-11`. La fiche FVD
du jeu aftermarket `FVD55599301B` publie une enveloppe de **108 × 45 × 27 mm**,
une masse de **0,18 kg la paire** et une construction en aluminium haute
résistance. Elle ne publie ni nuance, ni entraxe, ni axe, ni butée, ni tolérance.

Le modèle n'est donc pas une copie. Il conserve uniquement l'enveloppe publiée
et propose une topologie indépendante : plaque évidée, pont et chape intégrés,
alésage de pivot et deux perçages aveugles. Toutes ces interfaces restent des
hypothèses visibles dans le maître build123d.

## Pourquoi étudier le LPBF

L'intérêt n'est pas d'imprimer une simple plaque. Le concept réunit la plaque,
le pont et les deux oreilles de chape dans un seul solide et ouvre les poches
d'allègement vers l'extérieur, sans volume de poudre prisonnier. Cette
consolidation peut éviter pliage, soudure ou assemblage à faible volume et
autoriser une variante perforée ou personnalisée.

La comparaison avec CNC et tôle reste obligatoire. Si les mesures montrent que
la chape peut être usinée ou assemblée simplement, le LPBF ne sera pas retenu.

## Criblage mathématique exécuté

Sous un cas synthétique de `150 N` appliqué à `57 mm` du pivot et `+60 K` :

- section et inertie : `A = b t`, `I = b t³ / 12` ;
- flexion : `M = F L`, `sigma = M c / I` ;
- cisaillement rectangulaire : `tau = 1,5 F / (b t)` ;
- contrainte équivalente : `sqrt(sigma² + 3 tau²)` ;
- flèche de console : `delta = F L³ / (3 E I)` ;
- pression de matage du pivot : `F / (2 d t_oreille)` ;
- cisaillement double d'un axe candidat : `F / (2 pi d² / 4)` ;
- traction nette des deux oreilles : `F / (2 t_oreille (h_oreille-d))` ;
- pression moyenne de main, masse `rho V` et dilatation `alpha L delta_T` ;
- contrôle analytique du volume, BREP OCCT unique et relecture du STEP.

Ces calculs vérifient la cohérence du concept et du pipeline, pas la fonction
sur véhicule. La fatigue n'est pas calculable honnêtement sans cycle d'usage,
état de surface, population de défauts et courbe S-N qualifiée dans
l'orientation d'impression.

## Gates avant prototype

1. Acheter ou déposer une paire identifiée et mesurer pivot, butées, interfaces,
   jeux, portées et trajectoire du mécanisme.
2. Mesurer l'effort et les cas hors axe, puis définir un spectre cyclique.
3. Ajouter rayons, surépaisseurs et orientation LPBF à partir du procédé choisi.
4. Contrôler dimensionnellement, puis réaliser essais statiques, cycliques et
   ouverture d'urgence sur banc avant tout montage véhicule.

PhysicsNeMo n'est pas utilisé comme preuve : il faudra d'abord une base de cas
CAE ou d'essais corrélés. Le transfert SimReady reste également différé tant que
le prévol NVIDIA et les services Material/Physics ne sont pas sains.
