# Preuves F37 — définition de fabrication de la culasse quatre soupapes

Ce dossier publie les petites preuves traçables de la définition F37 : six
familles B-Rep exportées en STEP, les rapports de provenance et de criblage,
ainsi que les planches de revue CAO, huile, cinématique, résistance, LPBF et
NVIDIA. La source paramétrique reste sous `../../source/` et le
contrat sous `../../f37-manufacturing-definition.json`.

Le scan, le STL de culasse complet et les maillages bruts restent volontairement
hors du dépôt. `f37-printable-head-mesh-report.json` décrit leur audit sans les
publier. Les STEP présents sont des interfaces analytiques candidates; aucun
d'eux n'est une culasse de production complète.

`printable-proof` et `f37-printable-head-mesh-report.json` sont des identifiants
locaux historiques conservés pour la compatibilité de la chaîne de SHA. Ils
désignent uniquement un audit topologique et ne constituent jamais une preuve
d'imprimabilité ou une autorisation de fabrication.

## Résultats numériques à ne pas surinterpréter

- le noyau d'huile et le noyau gaz ne s'intersectent plus dans la booléenne
  exacte locale ;
- quatre plans d'appui sont détectés et cinq accès d'huile traversent la peau ;
- la variante porte-axes H24 × Y34, fenêtre Y36, emploie une charge ressort
  dynamique de 1 898 N puis une enveloppe de magnitude de réaction pivot de
  `2,15×`, soit 4 080,7 N. L'écran poutre donne 0,138794 mm et CalculiX donne
  une flèche fine de 0,093252 mm, sous la cible de 0,150 mm. La direction réelle
  de la réaction n'est pas connue et le maximum local de 208,734 MPa dépasse la
  limite-écran de 200 MPa; contact, précharge, fatigue et carte matière à chaud
  restent non qualifiés ;
- l'audit local du maillage retourne zéro sommet non-manifold, mais le
  validateur exact NVIDIA en signale 8 047 sur le même STL. Cette divergence
  reste bloquante ;
- OpenFOAM et FluidX3D sont en fort désaccord sur le refroidissement, et le
  calcul solide lié au coefficient OpenFOAM atteint 617,42 °C.
- l'audit LPBF exact détecte 0,184 cm³ de vide fermé, 1,259 % de voxels sans
  appui et une épaisseur p01 de 0,75 mm : les trois écrans sont bloquants.

Ces fichiers ne prouvent ni l'échelle absolue, ni l'ajustement Porsche 917, ni
une épaisseur minimale CT, ni la tenue en fatigue thermomécanique, ni la qualité
d'un procédé LPBF. Ils n'autorisent aucune impression métallique et aucun
démarrage moteur.

```text
metal_print_authorized = false
engine_start_authorized = false
rocker_pivot_resultant_load_complete = false
```

La publication est produite par une allowlist fail-closed, avec remplacement
atomique fichier par fichier et manifeste écrit en dernier :

```bash
make 917-manufacturing-f37-publish
```

`publication.json` lie ensuite chaque fichier par SHA-256. La vérification hors `work/`
se lance avec :

```bash
make 917-manufacturing-f37-evidence-check
```
