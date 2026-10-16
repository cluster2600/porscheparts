# Support 993 Turbo — reprise géométrique du 16 octobre 2026

Le candidat `bounded-webs` conserve les fixations de l'étude V6f et porte la
masse dense calculée à **1,262213 kg**, sous le plafond **1,30 kg** autorisé par
Maxime. Il est construit depuis des paramètres et des contours avant les
opérations booléennes, puis exporté et réimporté en STEP.

La [chaîne complète](../../../../docs/manufacturing/PART_WORKFLOW.md) relie cette
source à la surface contrôlée, aux calculs, aux supports, aux couches et au
guide d'atelier. La recette est
[`manufacturing/workflows/993-carrier.json`](../../../../manufacturing/workflows/993-carrier.json).

## Géométrie retenue

- [`build_bounded_webs.py`](build_bounded_webs.py) construit la pièce avec
  [`bounded-webs.json`](bounded-webs.json) et le
  [plan de construction](bounded-webs-plan.json).
- La peau supérieure et la peau inférieure font nominalement 1,5 mm ; les
  nervures de 2,8 mm et leur hauteur sont conservées.
- Les fenêtres sont réduites avant découpe. La paroi périphérique est définie
  par une translation de contour de 1,61 mm. La
  [borne géométrique](bounded-webs-wall-proof.json) démontre une séparation
  minimale de 1,59588 mm sur cette famille de courbes ; elle ne certifie pas
  toutes les arêtes de la pièce.
- Deux manchons locaux de rayon extérieur 4 mm entourent les perçages
  secondaires de rayon 2 mm, en conservant leurs axes.
- Le modèle reste dans l'enveloppe d'étude 592 × 73 × 52 mm. La platine
  centrale de 8 mm, ses quatre axes à entraxes 100 × 40 mm et les axes des
  extrémités distants de 560 mm sont conservés.

Ces cotes sont les paramètres explicites de l'étude. Les révisions ne
transforment pas les hypothèses de V6f en cotes Porsche mesurées.

## Contrôles et sélection

[`inspect_protected.py`](inspect_protected.py) compare les solides des régions
protégées : différence symétrique nulle sur la platine et les six régions
d'extrémité. Le contrôle indépendant V6f vérifie également les axes, les
passages d'outils et la paire de modèles F0.

[`compare.py`](compare.py) relance et compare les mêmes cas sur des maillages
C3D10 de tailles nominales 9 et 7 mm. La sélection exige simultanément :

1. masse ≤ 1,30 kg et contrôles des régions protégées réussis ;
2. déplacement et maximum de von Mises inférieurs à V6f dans les quatre
   comparaisons charge combinée / deux maillages / appuis rigides ou ressorts ;
3. bilan énergétique indépendant et superposition réussis aux seuils déclarés.

Les [critères](normal-webs-selection-criteria.json) distinguent explicitement
cette sélection comparative d'un admissible matériau. Les cas combinés
appliquent 4 000 N et 850 N·m. Le modèle des appuis souples utilise un total
de 1 000 N/mm par œil et par direction, réparti entre ses nœuds.

Le candidat passe ces comparaisons. Le maximum élastique du cas souple reste
supérieur à la limite utilisée dans le diagnostic plastique ; les calculs
non linéaires et les renforcements locaux ont donc leurs propres révisions
et décisions. Un passage comparatif réussi ne les remplace pas.

## Reproduction

La [base CAD macOS ARM64 / Python 3.10](cad-base-macos-arm64-python310.lock.txt)
épingle les 45 roues de l'installation autonome vérifiée, y compris build123d
0.11.1, OCCT sans VTK et NumPy. La procédure décrit son installation ; elle
évite de dépendre de l'environnement historique du checkout principal.

```sh
work/part-workflow/runtimes/design/bin/python -B \
  parts/993-eng-carrier-0001/source/design-20261016/build_bounded_webs.py \
  work/NOUVEAU_CANDIDAT
```

Pour reproduire tout le dossier, utiliser le lanceur et les runtimes de la
[procédure](../../../../docs/manufacturing/PART_WORKFLOW.md).

`normal-builder/cad.py` est une copie traçable du constructeur historique,
avec seulement les modifications nécessaires avant découpe et au calcul de
volume. Les essais antérieurs restent présents avec leurs paramètres : peau
épaisse, nervure amincie, pied tangent et décalages de surfaces terminées.
Les refus de masse, de mécanique ou de réimport STEP ne sont pas effacés.
