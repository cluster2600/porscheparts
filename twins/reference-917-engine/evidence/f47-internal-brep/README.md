# F47 — candidats B-Rep internes 2V / 4V

Ce dossier publie uniquement les preuves non propriétaires d'une première
comparaison 2 soupapes / 4 soupapes construite dans **la même peau externe F43
issue des 44 contours du scan**. La peau et les ailettes ne sont ni ovalisées,
ni remplacées par une boîte, ni recalculées par une primitive globale.

Le verdict est **FAIL-CLOSED**. Les deux STEP privés se relisent comme un solide
et une coque et passent `BRepCheck` exact, mais échouent `BOPAlgo` sur des
p-courbes et Gmsh 3D sur des intersections PLC. L'épaisseur minimale globale,
le retrait de poudre, l'échelle absolue et l'ajustement Porsche 917 ne sont pas
prouvés. Ces candidats ne sont donc ni CAE-ready, ni imprimables, ni autorisés
au démarrage moteur.

## Contenu publié

- `f47-internal-brep-public-report.json` : métriques exactes expurgées et portes;
- `917-head-f47-2v-4v-four-views.png` : même extérieur et ouvertures 2V/4V;
- `917-head-f47-2v-4v-sections.png` : coupe avec noyaux gaz/huile et composants;
- le contrat, le constructeur et le renderer sous
  `twins/reference-917-engine/`;
- le test autonome `tests/test_917_f47_internal_brep_variants.py`.

Les STEP, STL, MSH, rapports portant des coordonnées et le scan brut restent
hors Git. Le rapport public conserve leurs SHA-256 pour vérifier les artefacts
locaux autorisés sans les redistribuer.

## Résultat technique

| Porte | 2V | 4V |
|---|---:|---:|
| OCCT exact, solide/coque | PASS, 1/1 | PASS, 1/1 |
| bords libres / non-manifold | 0 / 0 | 0 / 0 |
| défauts `BOPAlgo_InvalidCurveOnSurface` | 8 | 32 |
| Gmsh 3D | FAIL PLC segment/facet | FAIL PLC facet/facet |
| sièges / guides / soupapes séparés | 2 / 2 / 2 | 4 / 4 / 4 |
| noyau huile BOP propre | PASS | PASS |
| noyau gaz BOP propre | FAIL (4) | FAIL (22) |
| distance gaz-huile, unité scan | 15,688 | 19,391 |
| épaisseur globale >= 1,5 mm | non prouvée | non prouvée |

La clairance fonctionnelle nominale minimale vaut 1,5 unité scan pour le 2V
et 3,160 pour le 4V. Cela n'est pas une carte d'épaisseur et ne devient une
mesure en millimètres que si la convention d'échelle non certifiée est vraie.

## Reproduction locale autorisée

Le constructeur requiert le STEP F43 privé avec le SHA-256 verrouillé dans le
contrat :

```bash
python3 twins/reference-917-engine/source/build_internal_brep_variants_f47.py \
  --outer-step /chemin/prive/917-head-scan-contour-repaired-v2-f43.step \
  --contract twins/reference-917-engine/internal-brep-contract-f47.json \
  --output work/917-f47-internals/final
make 917-f47-internal-brep-test
```

Le script s'arrête si le hash de la peau ne correspond pas. Toute nouvelle
itération doit reconstruire les p-courbes des raccords booléens, réussir
`BRepCheck`, `BOPAlgo` et Gmsh 3D, puis produire une vraie carte d'épaisseur et
un essai de dépoudrage avant de rouvrir une porte de CAE ou fabrication.
