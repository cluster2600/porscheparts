# F42 — vérification refroidissement et CHT de la culasse 917

## Verdict

La vérification F42 **ne valide pas** le refroidissement de la culasse et
n'autorise ni impression métal ni démarrage moteur. Elle apporte trois preuves
réelles et traçables :

1. la géométrie F41 exacte a été retessellée et retrouvée bit à bit ;
2. trois tentatives OpenFOAM sur cette géométrie ont été exécutées, mais aucune
   n'a satisfait la porte de convergence ;
3. le canal OpenFOAM F38 convergé, une corrélation indépendante et un calcul
   de conduction CalculiX sur le solide F41 exact montrent que la porte
   thermique de 260 °C n'est pas tenue.

Il s'agit d'un écran numérique fail-closed, pas d'une CHT complète ni d'une
validation physique.

## Géométrie réellement consommée

Le STEP F41 local a été maillé avec les paramètres OCCT du constructeur F41,
puis nettoyé avec la même chaîne. Le STL obtenu a le SHA-256
`2c1af796e851b680f67fd28b780d4b00fb8115efcf7e25a30d99361e6da1ac81`,
identique au rapport F41 publié : 262 554 triangles, une composante étanche,
aire 179 816,305 mm² conditionnelle et boîte 119,112 × 206,089 × 82,000 mm.

F42 ne modifie pas la forme extérieure. Les ouvertures d'admission,
d'échappement, de chambre et du porte-culbuteurs ne sont pas obturées par leurs
pièces d'assemblage. Un écoulement externe qui les traverse est donc optimiste
et ne représente pas la culasse installée.

## Conditions limites communes

| Entrée | Valeur | Statut |
|---|---:|---|
| Débit d'air par tête | 0,85 kg/s | hypothèse nominale héritée |
| Température d'air | 308,15 K (35 °C) | imposée |
| Pression statique sortie | 100 000 Pa | imposée |
| Température paroi OpenFOAM | 533,15 K (260 °C) | paroi isotherme, pas CHT |
| Charge thermique tête | 4 300 W | hypothèse nominale héritée |
| Porte température pont | 260 °C | écran numérique |
| Porte perte de charge | 6,7 kPa | écran numérique |

Les entrées ne sont pas ajustées pour forcer un résultat sous 260 °C.

## Méthode A — OpenFOAM

### Tentatives sur la forme F41 exacte

OpenFOAM 14, `foamRun` compressible, maillage `snappyHexMesh`, débit massique
imposé et paroi isotherme ont réellement été exécutés :

| Cas | Carénage | Modèle | Résultat |
|---|---:|---|---|
| `f42-shroud12-coarse-r3` | 12 mm | k-ω SST | divergence `NaN` à 13 itérations |
| `f42-shroud20-coarse-r4` | 20 mm | k-ω SST | divergence `NaN` à 13 itérations |
| `f42-shroud20-laminar-coarse-r5` | 20 mm | laminaire de secours | interrompu : pression oscillante, non convergé |

Les trois maillages passent le contrôle standard, mais les champs ne passent
pas la porte solveur. Aucun h ni Δp issu de ces trois champs n'est publié comme
résultat accepté.

### Référence OpenFOAM utilisable

Faute de champ F41 convergé, la méthode A quantitative reste le canal F38
réellement calculé, proche mais non identique aux passages F41. Sa maille fine
de 138 240 hexagones donne :

- h = 201,843 W/m²K ;
- Δp = 1 715,573 Pa ;
- erreur de bilan énergétique = 1,771 % ;
- erreur de bilan massique = 3,17×10⁻¹¹ ;
- variation h entre les deux mailles = 0,122 %.

Cette référence est un **proxy de canal**, jamais une preuve OpenFOAM de la
culasse F41 complète.

## Méthode B — corrélation indépendante

La seconde méthode utilise Gnielinski et Darcy–Weisbach, sans coefficient
ajusté sur F38. Les niveaux d'ailettes F41 donnent un jeu moyen de 4,096 mm ;
l'aire moyenne des profils donne une portée efficace de 90,435 mm et la
longueur d'écoulement vaut 206,089 mm.

| Passages équivalents | Capture | h [W/m²K] | Δp droit [Pa] | Porte 6,7 kPa |
|---:|---:|---:|---:|---|
| 13 | 70 % | 368,33 | 3 699,8 | passe |
| 13 | 100 % | 485,73 | 6 971,5 | **échoue** |
| 26 | 70 % | 215,764 | 1 090,667 | passe |
| 26 | 100 % | 284,05 | 2 041,4 | passe |

Le cas de comparaison est 26 passages et 70 % de capture, convention héritée
de la campagne F38/F39 et explicitement non mesurée.

## Recoupement

Entre le canal F38 convergé et la corrélation F41 sélectionnée :

- écart relatif h = **6,452 %**, porte <20 % passée ;
- écart relatif Δp = **57,296 %**, porte <20 % échouée.

L'accord sur h ne constitue pas une validation physique. L'écart de pression
interdit de clôturer le dessin du carénage et la puissance ventilateur.

## Température du solide

Deux niveaux ont été exécutés :

- réseau thermique conservatif avec aire F41 mesurée : pont à 370,68 °C avec
  Gnielinski et 379,55 °C avec le canal F38 ;
- CalculiX DC3D8, solide voxelisé depuis le STL F41 exact à 2,5 mm : 85 334
  hexagones, 99 391 nœuds, minimum 180,36 °C, médiane 321,88 °C,
  p95 414,38 °C, maximum **542,18 °C**.

CalculiX reçoit un h moyen de 215,76 W/m²K, 4 300 W sur la chambre voxelisée,
des films de ports hérités et une conductivité AlSi10Mg candidate dépendante de
la température. C'est une conduction séquentielle, pas un couplage fluide-
solide. La carte matière n'est pas qualifiée par coupons imprimés à chaud.

## Pourquoi la CHT reste fausse

- OpenFOAM impose 260 °C à la paroi au lieu d'échanger avec le solide ;
- CalculiX reçoit un h moyen, pas le champ local OpenFOAM ;
- les interfaces moteur ouvertes ne sont pas fermées par l'assemblage réel ;
- l'échelle absolue du scan, les fuites de carénage et la carte ventilateur ne
  sont pas mesurées ;
- les propriétés matière à chaud ne proviennent pas de coupons du procédé.

## Reproduction

Le STL F41 reste local conformément à la politique du dépôt. Vérifier son SHA
avant préparation. La consolidation reproductible est :

```bash
python3 twins/reference-917-engine/source/run_f42_cooling_cht.py \
  --contract twins/reference-917-engine/f42-cooling-cht-contract.json \
  --openfoam-case work/917-f42-cooling-cht/run/f42-shroud12-coarse-r3 \
  --openfoam-case work/917-f42-cooling-cht/run/f42-shroud20-coarse-r4 \
  --openfoam-case work/917-f42-cooling-cht/run/f42-shroud20-laminar-coarse-r5 \
  --calculix-report work/917-f42-cooling-cht/run/f42-calculix-p2p5-analytic-h/report.json \
  --output twins/reference-917-engine/evidence/f42-cooling-cht

make 917-f42-cooling-cht-check
```

## Prochaine porte d'ingénierie

Construire les fermetures d'assemblage mesurées, résoudre une CHT locale
fluide-solide avec deux mailles convergées, importer une carte ventilateur,
qualifier AlSi10Mg sur coupons du procédé puis corréler thermocouples et banc.
En l'état, augmenter arbitrairement h, retirer la charge d'échappement ou
ajouter un refroidissement huile non dimensionné ne serait pas une validation.
