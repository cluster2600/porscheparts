# F55 — diagnostic du plafond AdditiveFOAM

## Exécution réelle et portée

Trois diagnostics thermiques locaux sont exécutés sur Kali avec l'image
locale `a233511bef9b`, OpenFOAM `14-7b05503f98a8` et le binaire AdditiveFOAM
disponible dans le runtime privé. Chaque calcul atteint 120 microsecondes,
sans erreur fatale, avec retour du solveur égal à zéro. Aucune location
Vast supplémentaire n'est utilisée.

Les cas dérivent de l'initialisation locale de la couche 0 du témoin F50.
Ce n'est pas une reproduction de la campagne publiée complète, une
simulation de culasse entière ni une qualification de procédé.
Le diagnostic conserve notamment `nOuterCorrectors=0` et le schéma thermique
explicite du cas source : il ne démontre pas une hydrodynamique complète
du bain fondu. Le matériau configuré est AlSi10Mg, pas une carte CP1 qualifiée.

## Comparaison mesurée

| Configuration | Pic transitoire (K) | Maximum spatial à l'instant final (K) | Puissance absorbée maximale (W) |
|---|---:|---:|---:|
| Kelly, limite 3 300 K | 3 300,00 | 3 300,00 | 293,36 |
| Kelly, sans limite configurée | 4 741,37 | 4 209,63 | 293,66 |
| Absorption constante 0,35, sans limite configurée | 3 078,14 | 2 665,48 | 133,00 |

Les températures sont enregistrées à chaque pas par `volFieldValue`
(opération `max`). Les pics sont calculés sur toute la trajectoire, pas
seulement à l'instant final. Le module `fieldMinMax` initialement tenté
n'existe pas dans ce runtime : les premiers lancements ont été arrêtés
avant calcul et conservés comme échecs, puis les cas ont été recréés dans
un nouveau répertoire avec le module natif vérifié.

Le code source `thermo/TEqn.H` applique une pénalisation implicite lorsque
`T > Tmax`. `solutionControls.H` utilise `vGreat` lorsque `Tmax` est absent.
Le retrait de l'entrée sert ici à révéler la réponse non plafonnée, pas à
obtenir artificiellement une acceptation numérique.

## Interprétation et décisions

- Le plafonnement masque une surchauffe importante dans ce modèle.
- La loi d'absorption exerce une influence forte sur cette réponse.
- La valeur constante 0,35 est une perturbation diagnostique, pas une
  mesure fournisseur ni une recette retenue pour la fabrication.
- Une température sous 3 300 K ne prouve ni l'absence de vaporisation,
  ni la fidélité du bain fondu, ni la qualité de matière imprimée.
- La convergence du volume fondu sur trois maillages sous 5 % n'est pas
  démontrée ; ces cas ne sont pas admissibles pour entraîner PhysicsNeMo.

Il faut encore justifier l'absorption, le profil laser et les propriétés
matériau, puis vérifier le traitement des pertes et des changements de
phase avant une campagne de convergence. Aucun seuil de fabrication n'est
assoupli et aucune autorisation d'impression n'est accordée.

## Reproductibilité

`prepare_additive_cap_diagnostic_f55.py` copie uniquement `0`, `constant`
et `system` sans modifier les cas sources. Le témoin plafonné et le cas
déplafonné diffèrent seulement dans `fvSolution` ; le troisième diffère
ensuite seulement dans `heatSourceDict`. Ces invariants sont testés, ainsi
que le refus d'écraser un répertoire de sortie. Le post-traitement teste la
distinction entre pic et température finale et refuse les valeurs non finies.

Les configurations détaillées, journaux, exports VTK et rapports liés par
SHA-256 restent conservés dans les sorties privées F55 sur Kali.
