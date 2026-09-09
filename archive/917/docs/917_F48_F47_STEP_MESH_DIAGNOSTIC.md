# F48 — diagnostic du maillage des STEP internes F47

## Conclusion

Les deux STEP de culasse F47 sont **refusés pour le maillage volumique**. Le
défaut est localisé aux p-curves des arêtes du noyau gaz, puis amplifié par la
soustraction booléenne dans la tête. Il ne provient ni du noyau d'huile, ni
d'une intersection gaz/huile démontrée, ni d'une géométrie extérieure de
remplacement.

F48 est un diagnostic. Il ne produit aucune CAO réparée, aucun maillage de
calcul et aucune preuve CFD, CHT, structure ou impression 3D.

## Résultats mesurés

| variante | solide | `BRepCheck` exact | défauts `InvalidCurveOnSurface` | faces/arêtes fautives | Gmsh 3D |
|---|---|---:|---:|---:|---|
| 2V | noyau gaz | passe | 4 | 3 / 4 | non tenté isolément |
| 2V | noyau huile | passe | 0 | 0 / 0 | non nécessaire au diagnostic causal |
| 2V | tête après soustraction | passe | 8 | 5 / 8 | échec `segment/facette` |
| 4V | noyau gaz | passe | 22 | 10 / 18 | non tenté isolément |
| 4V | noyau huile | passe | 0 | 0 / 0 | non nécessaire au diagnostic causal |
| 4V | tête après soustraction | passe | 32 | 17 / 28 | échec `facette/facette` |

Le point important est que `BRepCheck=True` n'est pas une preuve de préparation
CAE : `BOPAlgo_ArgumentAnalyzer` détecte les incohérences courbe 3D / courbe 2D
sur surface, et Gmsh les transforme ensuite en intersections de contraintes
PLC pendant la tétraédrisation.

Les 93 références d'entités fautives (faces et arêtes, avant et après
soustraction) sont suivies dans le
[`diagnostic-report.json`](../twins/reference-917-engine/evidence/f48-mesh-diagnostic/diagnostic-report.json)
par des identifiants opaques déterministes. Les indices OCCT et les boîtes de
localisation exactes restent dans un rapport local de 34 895 octets, lié par le
SHA-256 `0fdaa6491d4c4c16190856e1858ed76d5ef0609eabab0ee9322176d2d3841ed8`.
Ni ces coordonnées ni les STEP privés ne sont copiés dans Git.

## Cause et limite de l'attribution

Les faits bornent la cause au noyau gaz : 4 puis 22 défauts avant soustraction,
zéro pour l'huile, 8 puis 32 dans les têtes. La construction F47 fusionne une
chambre circulaire, des cylindres circulaires coaxiaux de siège, gorge et guide,
et des cylindres circulaires inclinés pour les conduits. Les arêtes rognées de
ces jonctions sont donc la famille causale la plus probable.

Cette attribution au type de jonction a une confiance moyenne faute d'historique
de nommage OCCT persistant à travers STEP. Les familles de défauts, les solides
et les entités sont en revanche localisés exactement dans le rapport privé.

## Correction chirurgicale proposée

1. Reprojeter uniquement les p-curves des couples arête/face fautifs du noyau
   gaz à partir des courbes 3D et surfaces support existantes.
2. Exiger zéro défaut `InvalidCurveOnSurface` avant export et après un aller-
   retour STEP. Si cela échoue, reconstruire seulement les jonctions internes
   concernées avec recouvrement explicite et partition OCC avant fusion.
3. Soustraire le noyau gaz accepté et le noyau huile inchangé du même fichier
   extérieur F43 verrouillé par SHA-256.
4. Comparer les signatures géométriques des faces extérieures hors ouvertures,
   imposer une distance de peau nulle, puis relancer Gmsh sur trois tailles de
   maille.

Une couture ou réparation globale de la tête est interdite : elle pourrait
déplacer la peau issue du scan. Aucun proxy, aucune ellipse et aucun ovale ne
peut remplacer la géométrie F43.

## Portes fermées

La réparation locale n'a pas encore été exécutée. Les portes BOP zéro défaut,
maillage 2V/4V, convergence, verrou de peau après réparation, CFD/CHT/FEA,
impression métal et démarrage moteur restent donc toutes fermées.

## Reproduction de la publication publique

Le script de diagnostic public charge les STEP uniquement quand l'opérateur lui
fournit explicitement un répertoire privé. Il refuse d'écrire son rapport à
indices et coordonnées dans le dépôt. Ses deux modes séparent les dépendances
OCCT et Gmsh. Le script de publication reconstruit et vérifie uniquement le
rapport expurgé et son manifeste.

```bash
# Dans l'image OCCT; chemins privés fournis par l'opérateur
python3 twins/reference-917-engine/source/diagnose_private_f47_step_mesh_f48.py \
  --mode occt --private-root /CHEMIN/PRIVE \
  --private-output /SORTIE/HORS/DEPOT/f48-occt.json --project-root .

# Dans l'image Gmsh; même règle de confinement
python3 twins/reference-917-engine/source/diagnose_private_f47_step_mesh_f48.py \
  --mode gmsh --private-root /CHEMIN/PRIVE \
  --private-output /SORTIE/HORS/DEPOT/f48-gmsh.json --project-root .

python3 twins/reference-917-engine/source/publish_mesh_diagnostic_f48.py \
  --project-root .
python3 twins/reference-917-engine/source/publish_mesh_diagnostic_f48.py \
  --project-root . --check
python3 tests/test_917_mesh_diagnostic_f48.py -v
```
