# Planche 21 — raffinement local du vrai maillage EF

Cette planche compare le maillage EF7 original au raffinement adaptatif 002
réellement terminé : RC0, quatre passes, 160 964 nœuds et 86 544 éléments T10,
contre 159 121 nœuds et 85 315 T10 au départ. Les nœuds existants, les ensembles
nodaux et les 3 218 facettes protégées sont conservés. Le reçu du calcul atteste
un volume mesuré égal à celui de départ et des jacobiens tous positifs.

Les huit panneaux montrent deux boîtes fixes, avant/après, dans deux projections
orthographiques XY/XZ. Les coordonnées sont celles des vrais INP, sans rotation
de pose, déformation ni amplification. La planche décrit un **maillage
géométriquement contrôlé** ; la convergence des contraintes reste à étudier.
Les résultats mécaniques ultérieurs sont documentés séparément.

| Boîte de mesure fixe | Maximum original (mm) | Maximum final (mm) | Cible fixe (mm) |
|---|---:|---:|---:|
| Pic initial rigide EF7 | 3.4175796812885544 | 1.3844416177416714 | 1.3844416177456211 |
| Pic initial K1000 EF7 | 2.5172357815814346 | 1.2586178907902892 | 1.2586178907907173 |

Les cibles sont la moitié du maximum des six arêtes du **tétraèdre du pic
initial** : respectivement 2.7688832354912423 et 2.5172357815814346 mm.
Elles ne sont pas la moitié du maximum de chaque boîte. Les valeurs binary64
complètes sont conservées ; la comparaison `maximum final ≤ cible` précède
l’arrondi d’affichage. Aucun raffinement global par deux n’est affirmé.

## Arêtes représentées et données

L’extraction lit les vrais INP avec le lecteur `audit_energy.read_mesh`, puis
réutilise le mesureur figé `8e385ac9`. Chaque cellule dont le centroïde est dans
la boîte fournit ses six arêtes **entières**. S’y ajoutent toutes les arêtes
dont les deux extrémités sont dans la boîte. Seules les paires d’identifiants
identiques sont dédupliquées pour le dessin ; les arêtes ne sont pas raccourcies
à la frontière de la boîte.

| Boîte | Cellules avant/après | Arêtes uniques avant/après |
|---|---:|---:|
| Pic initial rigide | 6 / 64 | 19 / 132 |
| Pic initial K1000 | 3 / 23 | 12 / 62 |

Le [JSON géométrique](data/figure-data.json) de 25 240 octets contient toutes
les positions, identifiants et arêtes nécessaires. Le rendu n’importe aucun
maillage ni sortie de solveur. Les limites des axes sont communes à chaque
comparaison. SVG/PDF rasterisent les arêtes, sans échantillonnage de leur liste.

Les [preuves du maillage](evidence/H2-root-terminal.json), son
[assessment complet](evidence/H2-assessment.json), les reçus d’extraction et
de rendu, ainsi que les sources et leurs diffs de présentation sont inclus.
[source-provenance.json](source-provenance.json) lie les copies à leurs SHA
originaux ; [manifest.json](manifest.json) couvre l’ensemble de cette capsule.
Les sources, données et trois images restent identiques aux fichiers relus.

## Reproduction portable

Le vrai rejeu depuis le répertoire courant `/` est terminé : RC0, 2,882554 s,
groupe propriétaire fermé, 211 fichiers du runtime inchangés. PNG, SVG et PDF
ont les trois SHA attendus. Root a ensuite inspecté le PNG final et la première
page du PDF. Le [reçu de publication séparé](../local-refinement-root-publication-20261017.json)
lie ces faits au [rejeu réel](evidence/portable-replay-closeout.json).

Le renderer utilise Python 3.10.11, NumPy 2.2.6, Matplotlib 3.10.8, Pillow 11.3.0
et DejaVu Sans déjà présents ; le runtime n’est pas embarqué. Copier ce dossier
entier, choisir une **sortie neuve**, puis, depuis n’importe quel répertoire :

```sh
CARRIER_FIGURE=/chemin/absolu/vers/local-refinement-20261017
CARRIER_OUTPUT=/chemin/absolu/vers/une-sortie-neuve
CARRIER_RENDER_PYTHON=/chemin/vers/python3.10
cd /
python3 -B "$CARRIER_FIGURE/verify.py"
python3 -B "$CARRIER_FIGURE/selfcheck.py"
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  "$CARRIER_RENDER_PYTHON" -B "$CARRIER_FIGURE/render.py" render \
  "$CARRIER_FIGURE/data/figure-data.json" \
  a88bbb99453ea311f2e8dbce3ef1c9616436fba80ddeedd01caeb2e92a497ed1 \
  "$CARRIER_OUTPUT"
```

Le rendu impose 95 s internes et CPU 90/91 s, un thread configuré et zéro worker ;
la supervision réelle conserve 120 s externes et les grâces 10+10 s. Il ne lance
aucun calcul mécanique. Les valeurs `FEA_started=false` dans ses reçus décrivent
ce seul travail de maillage et d’image.

Le [README de préparation](history/prepublication-README.md), son
[manifeste](history/work-capsule-manifest.json) et `publication.json` sont
conservés à l’octet : leurs anciens indicateurs faux décrivent l’état antérieur
au rejeu et à la QA. La présente documentation et le reçu séparé enregistrent
les étapes ultérieures sans réécrire ces preuves historiques.
